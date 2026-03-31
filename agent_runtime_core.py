#!/usr/bin/env python3
"""
AGENT RUNTIME CORE (Versão 1.1)
Orquestrador central responsável por coordenar agentes, tools, memória e execução de workflows

COMPONENTES:
- task_intake: Recebe e valida inputs
- planner: Cria planos de execução
- workflow_router: Direciona para workflows específicos
- agent_dispatcher: Gerencia execução de agentes
- policy_engine: Verifica políticas e segurança
- approval_gate: Gerencia aprovações
- validator: Valida resultados
- artifact_manager: Gerencia artefatos
- memory_manager: Persistência de contexto

FLUXO:
1. Receber input → 2. Classificar → 3. Criar agent_run → 4. Carregar contexto → 
5. Buscar domain_rules → 6. Gerar plano → 7. Executar steps → 8. Validar → 
9. Registrar logs → 10. Gerar artifacts → 11. Solicitar approval → 12. Encerrar

REGRAS DE OURO:
- Nunca executar ação sem log
- Nunca executar ação de risco sem policy check
- Nunca executar tool sem registro em tool_calls
- Sempre validar saída antes de seguir
"""

import json
import uuid
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import defaultdict
import importlib.util

# Configuração de paths
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "kitchen_data"
LOGS_DIR = ROOT_DIR / "logs"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
RUNTIME_DIR = ROOT_DIR / "runtime"

# Criar diretórios necessários
for d in [LOGS_DIR, ARTIFACTS_DIR, RUNTIME_DIR]:
    d.mkdir(exist_ok=True)


class WorkflowType(Enum):
    """Tipos de workflow suportados"""
    KITCHEN = auto()           # Kitchen Control
    FINANCIAL = auto()         # DRE, Fixed Cost
    PROCUREMENT = auto()       # Compras
    PRICING = auto()           # Precificação
    AUDIT = auto()             # Auditoria
    CALIBRATION = auto()       # Calibração
    REPORTING = auto()         # Relatórios
    RECONCILIATION = auto()    # Reconciliação
    FULL_PIPELINE = auto()      # Pipeline completo
    UNKNOWN = auto()


class RiskLevel(Enum):
    """Níveis de risco"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ExecutionStatus(Enum):
    """Status de execução"""
    PENDING = "pending"
    RUNNING = "running"
    VALIDATING = "validating"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ToolCall:
    """Registro de chamada de tool"""
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    status: str
    timestamp_start: str
    timestamp_end: Optional[str]
    error: Optional[str]
    policy_violations: List[str]


@dataclass
class ExecutionStep:
    """Passo de execução"""
    step_id: str
    step_number: int
    action: str
    tool: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    validation_result: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.NONE
    requires_approval: bool = False
    approved_by: Optional[str] = None


@dataclass
class AgentRun:
    """Execução de agente"""
    run_id: str
    workflow_type: WorkflowType
    status: ExecutionStatus
    input_data: Dict[str, Any]
    steps: List[ExecutionStep]
    context: Dict[str, Any]
    artifacts: List[str]
    logs: List[str]
    created_at: str
    updated_at: str
    domain_rules: List[str]
    policy_checks: List[str]
    memory_refs: List[str]


class PolicyEngine:
    """Motor de políticas e segurança"""
    
    def __init__(self):
        self.policies = self._load_policies()
        self.violations = []
    
    def _load_policies(self) -> Dict:
        """Carrega políticas do sistema"""
        return {
            "risk_thresholds": {
                "financial": {
                    "max_variance": 0.15,  # 15%
                    "requires_approval": ["price_change", "cost_adjustment"]
                },
                "data_integrity": {
                    "required_fields": ["event_id", "n_ctt", "timestamp"],
                    "trace_mode_mandatory": True
                },
                "operations": {
                    "auto_execute": ["read", "validate", "calculate"],
                    "manual_approval": ["write", "update", "delete", "adjust"]
                }
            },
            "forbidden_actions": [
                "delete_without_backup",
                "update_without_log",
                "execute_without_policy_check",
                "modify_financial_data_directly"
            ]
        }
    
    def check_action(self, action: str, inputs: Dict, context: Dict) -> Tuple[bool, List[str], RiskLevel]:
        """
        Verifica se ação pode ser executada
        
        Retorna: (permitido, violações, nível_risco)
        """
        violations = []
        risk_level = RiskLevel.NONE
        
        # Regra 1: Nunca executar sem log
        if not context.get("log_enabled", False):
            violations.append("Ação sem logging habilitado")
            risk_level = RiskLevel.HIGH
        
        # Regra 2: Verificar ações proibidas
        if action in self.policies["forbidden_actions"]:
            violations.append(f"Ação proibida: {action}")
            return False, violations, RiskLevel.CRITICAL
        
        # Regra 3: Verificar campos obrigatórios
        if action.startswith("write") or action.startswith("update"):
            for field in self.policies["risk_thresholds"]["data_integrity"]["required_fields"]:
                if field not in inputs:
                    violations.append(f"Campo obrigatório ausente: {field}")
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Regra 4: Verificar se precisa de aprovação
        auto_execute = self.policies["risk_thresholds"]["operations"]["auto_execute"]
        requires_manual = self.policies["risk_thresholds"]["operations"]["manual_approval"]
        
        action_category = action.split("_")[0] if "_" in action else action
        
        if action_category in requires_manual:
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            violations.append(f"Ação '{action}' requer aprovação manual")
        
        # Regra 5: Verificar variação financeira
        if "variance" in inputs:
            variance = abs(float(inputs.get("variance", 0)))
            if variance > self.policies["risk_thresholds"]["financial"]["max_variance"]:
                violations.append(f"Variação {variance:.1%} excede limite de 15%")
                risk_level = RiskLevel.HIGH
        
        # Determinar se é permitido
        is_allowed = len(violations) == 0 or risk_level.value < RiskLevel.CRITICAL.value
        
        return is_allowed, violations, risk_level


class MemoryManager:
    """Gerenciador de memória e contexto"""
    
    def __init__(self):
        self.memory_cache = {}
        self.context_files = {
            "events": DATA_DIR / "events_consolidated.csv",
            "inventory": DATA_DIR / "inventory.json",
            "recipes": DATA_DIR / "recipes.json",
            "cmv": DATA_DIR / "cmv_log.json",
            "decisions": DATA_DIR / "decisions.json"
        }
    
    def load_minimal_context(self, event_id: Optional[str] = None) -> Dict:
        """Carrega contexto mínimo necessário"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "event_id": event_id,
            "base_path": str(ROOT_DIR),
            "data_path": str(DATA_DIR)
        }
        
        if event_id:
            # Carregar dados específicos do evento
            event_data = self._load_event_data(event_id)
            context["event_data"] = event_data
        
        return context
    
    def _load_event_data(self, event_id: str) -> Dict:
        """Carrega dados de evento específico"""
        # Simplificado - em produção buscar de JSON/CSV
        return {"event_id": event_id, "status": "loaded"}
    
    def get_domain_rules(self, workflow_type: WorkflowType) -> List[str]:
        """Busca regras de domínio relevantes"""
        rules_by_workflow = {
            WorkflowType.KITCHEN: ["recipe_validation", "cost_calculation", "yield_estimation"],
            WorkflowType.FINANCIAL: ["margin_thresholds", "allocation_rules", "audit_trail"],
            WorkflowType.PROCUREMENT: ["supplier_evaluation", "price_tolerance", "stock_levels"],
            WorkflowType.PRICING: ["target_margins", "competitive_analysis", "cost_plus"],
            WorkflowType.AUDIT: ["consistency_checks", "variance_limits", "traceability"],
            WorkflowType.CALIBRATION: ["pattern_detection", "adjustment_thresholds", "rollback_safety"],
            WorkflowType.REPORTING: ["data_completeness", "format_standards", "distribution"],
            WorkflowType.RECONCILIATION: ["variance_tolerance", "investigation_triggers", "sign_off_requirements"]
        }
        
        return rules_by_workflow.get(workflow_type, ["base_rules"])
    
    def persist_execution(self, run: AgentRun):
        """Persiste execução na memória"""
        memory_file = RUNTIME_DIR / f"run_{run.run_id}.json"
        
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(run), f, indent=2, default=str)
        
        # Atualizar também em MEMORY.md se existir
        self._update_memory_md(run)
    
    def _update_memory_md(self, run: AgentRun):
        """Atualiza MEMORY.md com execução"""
        memory_file = ROOT_DIR / "MEMORY.md"
        
        entry = f"""
## Execução {run.run_id}
- **Data:** {run.created_at[:10]}
- **Workflow:** {run.workflow_type.name}
- **Status:** {run.status.value}
- **Steps:** {len(run.steps)}
- **Artefatos:** {', '.join(run.artifacts) if run.artifacts else 'Nenhum'}
"""
        
        if memory_file.exists():
            with open(memory_file, 'a', encoding='utf-8') as f:
                f.write(entry)


class ArtifactManager:
    """Gerenciador de artefatos"""
    
    def __init__(self):
        self.artifact_registry = {}
    
    def register_artifact(self, run_id: str, artifact_type: str, path: str, metadata: Dict) -> str:
        """Registra artefato gerado"""
        artifact_id = f"ART-{uuid.uuid4().hex[:8].upper()}"
        
        self.artifact_registry[artifact_id] = {
            "run_id": run_id,
            "type": artifact_type,
            "path": path,
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        return artifact_id
    
    def validate_artifact(self, artifact_id: str) -> bool:
        """Valida se artefato existe e está consistente"""
        if artifact_id not in self.artifact_registry:
            return False
        
        artifact = self.artifact_registry[artifact_id]
        path = Path(artifact["path"])
        
        return path.exists() and path.stat().st_size > 0


class WorkflowRouter:
    """Roteador de workflows"""
    
    def __init__(self):
        self.engine_map = {
            WorkflowType.KITCHEN: ["kitchen_control_layer.py", "kitchen_engine.py"],
            WorkflowType.FINANCIAL: ["dre_engine.py", "fixed_cost_engine.py"],
            WorkflowType.PROCUREMENT: ["procurement_feedback_engine.py"],
            WorkflowType.PRICING: ["item_pricing_engine.py"],
            WorkflowType.AUDIT: ["financial_truth_audit.py"],
            WorkflowType.CALIBRATION: ["system_calibration_engine.py"],
            WorkflowType.REPORTING: [
                "executive_report_engine.py",
                "ceo_dashboard_engine.py",
                "sales_dashboard_engine.py"
            ],
            WorkflowType.RECONCILIATION: ["event_reconciliation_engine.py"]
        }
    
    def classify_input(self, input_data: Dict) -> WorkflowType:
        """Classifica input no workflow apropriado"""
        
        # Palavras-chave para classificação
        keywords = {
            WorkflowType.KITCHEN: ["receita", "receipe", "produção", "cozinha", "custo"],
            WorkflowType.FINANCIAL: ["dre", "margem", "lucro", "fixed", "rateio"],
            WorkflowType.PROCUREMENT: ["compra", "fornecedor", "estoque", "preço"],
            WorkflowType.PRICING: ["preço", "pricing", "venda", "tarifa"],
            WorkflowType.AUDIT: ["auditoria", "validação", "consistência", "check"],
            WorkflowType.CALIBRATION: ["calibração", "ajuste", "padrão", "erro"],
            WorkflowType.REPORTING: ["relatório", "dashboard", "executivo", "resumo"],
            WorkflowType.RECONCILIATION: ["reconciliação", "real", "contábil", "conferência"],
            WorkflowType.FULL_PIPELINE: ["completo", "tudo", "pipeline", "full"]
        }
        
        text = str(input_data).lower()
        scores = defaultdict(int)
        
        for wf_type, words in keywords.items():
            for word in words:
                if word in text:
                    scores[wf_type] += 1
        
        if scores:
            return max(scores, key=scores.get)
        
        return WorkflowType.UNKNOWN
    
    def get_engine_sequence(self, workflow_type: WorkflowType) -> List[str]:
        """Retorna sequência de engines para workflow"""
        return self.engine_map.get(workflow_type, [])


class Validator:
    """Validador de resultados"""
    
    def validate_step_output(self, step: ExecutionStep) -> Tuple[bool, str]:
        """Valida saída de um passo"""
        
        # Regra: SEMPRE validar saída antes de seguir
        if not step.outputs:
            return False, "Sem saída gerada"
        
        # Validar estrutura
        required_fields = ["status", "timestamp"]
        for field in required_fields:
            if field not in step.outputs:
                return False, f"Campo obrigatório ausente: {field}"
        
        # Validar status
        if step.outputs.get("status") == "error":
            return False, f"Erro na execução: {step.outputs.get('error', 'Desconhecido')}"
        
        # Validar integridade
        if "data" in step.outputs:
            data = step.outputs["data"]
            if isinstance(data, dict):
                # Verificar trace_mode se aplicável
                if "trace_mode" in data and data["trace_mode"] not in ["direct", "inferred", "allocated"]:
                    return False, "trace_mode inválido"
        
        return True, "Validação OK"
    
    def validate_artifact(self, artifact_path: Path) -> Tuple[bool, str]:
        """Valida artefato gerado"""
        
        if not artifact_path.exists():
            return False, "Artefato não encontrado"
        
        if artifact_path.stat().st_size == 0:
            return False, "Artefato vazio"
        
        # Validar JSON se aplicável
        if artifact_path.suffix == ".json":
            try:
                with open(artifact_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                return False, f"JSON inválido: {e}"
        
        return True, "Artefato válido"


class ApprovalGate:
    """Portão de aprovação"""
    
    def __init__(self):
        self.pending_approvals = {}
    
    def requires_approval(self, action: str, risk_level: RiskLevel) -> bool:
        """Determina se ação requer aprovação"""
        
        if risk_level.value >= RiskLevel.HIGH.value:
            return True
        
        sensitive_actions = [
            "price_update", "cost_adjustment", "inventory_correction",
            "recipe_modification", "supplier_change", "margin_override"
        ]
        
        return any(sa in action.lower() for sa in sensitive_actions)
    
    def request_approval(self, run_id: str, step: ExecutionStep, reason: str) -> str:
        """Solicita aprovação manual"""
        
        approval_id = f"APR-{uuid.uuid4().hex[:8].upper()}"
        
        self.pending_approvals[approval_id] = {
            "run_id": run_id,
            "step_id": step.step_id,
            "action": step.action,
            "reason": reason,
            "requested_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Log da solicitação
        print(f"\n🚦 APROVAÇÃO NECESSÁRIA: {approval_id}")
        print(f"   Ação: {step.action}")
        print(f"   Motivo: {reason}")
        print(f"   Execute: /approve {approval_id}")
        
        return approval_id
    
    def check_approval(self, approval_id: str) -> Tuple[bool, str]:
        """Verifica status de aprovação"""
        
        if approval_id not in self.pending_approvals:
            return False, "Aprovação não encontrada"
        
        approval = self.pending_approvals[approval_id]
        
        if approval["status"] == "approved":
            return True, approval.get("approved_by", "sistema")
        elif approval["status"] == "rejected":
            return False, "Rejeitado"
        
        return False, "Pendente"


class AgentDispatcher:
    """Despachador de agentes e execução"""
    
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.approval_gate = ApprovalGate()
        self.validator = Validator()
        self.artifact_manager = ArtifactManager()
        self.memory_manager = MemoryManager()
    
    def dispatch(self, engine_name: str, inputs: Dict, context: Dict) -> Dict:
        """Executa engine Python"""
        
        engine_path = ROOT_DIR / engine_name
        
        if not engine_path.exists():
            return {
                "status": "error",
                "error": f"Engine não encontrado: {engine_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            # Executar como subprocess
            result = subprocess.run(
                [sys.executable, str(engine_path)],
                capture_output=True,
                text=True,
                cwd=str(ROOT_DIR),
                timeout=300  # 5 minutos timeout
            )
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "engine": engine_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout na execução",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class Planner:
    """Planejador de execução"""
    
    def create_plan(self, workflow_type: WorkflowType, context: Dict) -> List[ExecutionStep]:
        """Cria plano de execução baseado no tipo de workflow"""
        
        plans = {
            WorkflowType.FULL_PIPELINE: [
                {"action": "validate_inputs", "tool": "kitchen_control_layer", "inputs": {}},
                {"action": "calculate_costs", "tool": "kitchen_control_layer", "inputs": {}},
                {"action": "allocate_fixed_costs", "tool": "fixed_cost_engine", "inputs": {}},
                {"action": "generate_dre", "tool": "dre_engine", "inputs": {}},
                {"action": "audit_consistency", "tool": "financial_truth_audit", "inputs": {}},
                {"action": "calibrate_system", "tool": "system_calibration", "inputs": {}},
                {"action": "generate_reports", "tool": "executive_report", "inputs": {}},
                {"action": "generate_dashboard", "tool": "ceo_dashboard", "inputs": {}},
                {"action": "reconcile", "tool": "event_reconciliation", "inputs": {}}
            ],
            WorkflowType.FINANCIAL: [
                {"action": "calculate_cmv", "tool": "kitchen_control", "inputs": {}},
                {"action": "allocate_fixed", "tool": "fixed_cost", "inputs": {}},
                {"action": "generate_dre", "tool": "dre_engine", "inputs": {}}
            ],
            WorkflowType.REPORTING: [
                {"action": "executive_report", "tool": "executive_report", "inputs": {}},
                {"action": "ceo_dashboard", "tool": "ceo_dashboard", "inputs": {}},
                {"action": "sales_dashboard", "tool": "sales_dashboard", "inputs": {}}
            ]
        }
        
        default_plan = [
            {"action": "analyze_input", "tool": "analyzer", "inputs": {}},
            {"action": "execute_main", "tool": "main_engine", "inputs": {}}
        ]
        
        plan_template = plans.get(workflow_type, default_plan)
        
        steps = []
        for i, step_def in enumerate(plan_template, 1):
            step = ExecutionStep(
                step_id=f"STEP-{uuid.uuid4().hex[:8].upper()}",
                step_number=i,
                action=step_def["action"],
                tool=step_def["tool"],
                inputs=step_def["inputs"]
            )
            steps.append(step)
        
        return steps


class AgentRuntimeCore:
    """Runtime central - orquestrador principal"""
    
    def __init__(self):
        self.task_intake = None  # Simplificado
        self.planner = Planner()
        self.workflow_router = WorkflowRouter()
        self.agent_dispatcher = AgentDispatcher()
        self.policy_engine = PolicyEngine()
        self.memory_manager = MemoryManager()
        self.validator = Validator()
        self.approval_gate = ApprovalGate()
        self.artifact_manager = ArtifactManager()
        
        self.active_runs = {}
        self.log_buffer = []
    
    def _log(self, message: str, level: str = "INFO"):
        """Logging centralizado - REGRA: Nunca sem log"""
        log_entry = f"[{datetime.now().isoformat()}] [{level}] {message}"
        self.log_buffer.append(log_entry)
        print(log_entry)
    
    def execute_full_pipeline(self, input_data: Dict) -> AgentRun:
        """
        EXECUÇÃO DO PIPELINE COMPLETO
        
        Segue os 12 passos definidos:
        1. Receber input → 2. Classificar → 3. Criar agent_run → 4. Carregar contexto → 
        5. Buscar domain_rules → 6. Gerar plano → 7. Executar steps → 8. Validar → 
        9. Registrar logs → 10. Gerar artifacts → 11. Solicitar approval → 12. Encerrar
        """
        
        self._log("="*80, "START")
        self._log("AGENT RUNTIME CORE v1.1 - Iniciando execução", "START")
        self._log("="*80, "START")
        
        # PASSO 1: Receber Input
        self._log("PASSO 1/12: Recebendo input...")
        
        # PASSO 2: Classificar Workflow
        self._log("PASSO 2/12: Classificando tipo de workflow...")
        workflow_type = self.workflow_router.classify_input(input_data)
        self._log(f"   Workflow identificado: {workflow_type.name}")
        
        if workflow_type == WorkflowType.FULL_PIPELINE or workflow_type == WorkflowType.UNKNOWN:
            workflow_type = WorkflowType.FULL_PIPELINE
            self._log("   Executando FULL PIPELINE (todos os engines)")
        
        # PASSO 3: Criar Agent Run
        self._log("PASSO 3/12: Criando agent_run...")
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        run = AgentRun(
            run_id=run_id,
            workflow_type=workflow_type,
            status=ExecutionStatus.PENDING,
            input_data=input_data,
            steps=[],
            context={},
            artifacts=[],
            logs=self.log_buffer.copy(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            domain_rules=[],
            policy_checks=[],
            memory_refs=[]
        )
        self.active_runs[run_id] = run
        
        # PASSO 4: Carregar Contexto Mínimo
        self._log("PASSO 4/12: Carregando contexto mínimo...")
        event_id = input_data.get("event_id")
        context = self.memory_manager.load_minimal_context(event_id)
        run.context = context
        
        # PASSO 5: Buscar Domain Rules
        self._log("PASSO 5/12: Buscando domain_rules relevantes...")
        domain_rules = self.memory_manager.get_domain_rules(workflow_type)
        run.domain_rules = domain_rules
        self._log(f"   Regras carregadas: {', '.join(domain_rules)}")
        
        # PASSO 6: Gerar Plano
        self._log("PASSO 6/12: Gerando plano de execução...")
        steps = self.planner.create_plan(workflow_type, context)
        run.steps = steps
        self._log(f"   Plano criado: {len(steps)} steps")
        
        for step in steps:
            self._log(f"   - Step {step.step_number}: {step.action} ({step.tool})")
        
        # PASSO 7: Executar Steps
        self._log("PASSO 7/12: Executando steps...")
        run.status = ExecutionStatus.RUNNING
        
        for step in steps:
            self._log(f"\n   Executando Step {step.step_number}: {step.action}")
            
            # Verificar política ANTES de executar
            permitted, violations, risk = self.policy_engine.check_action(
                step.action, step.inputs, context
            )
            
            if not permitted:
                self._log(f"   ❌ BLOQUEADO por política: {violations[0]}", "ERROR")
                step.status = "blocked"
                continue
            
            # Check de aprovação
            if self.approval_gate.requires_approval(step.action, risk):
                self._log(f"   ⚠️  Requer aprovação (risco: {risk.name})")
                step.requires_approval = True
                step.risk_level = risk
                
                approval_id = self.approval_gate.request_approval(
                    run_id, step, f"Risco {risk.name}: {', '.join(violations)}"
                )
                
                # Simular aprovação (em produção, esperar input humano)
                step.approved_by = "AUTO_APPROVED" if risk.value < RiskLevel.HIGH.value else None
                
                if not step.approved_by:
                    self._log(f"   ⏸️  Aguardando aprovação manual: {approval_id}")
                    continue
            
            # Executar tool
            step.started_at = datetime.now().isoformat()
            
            # Mapear tool para engine
            engine_map = {
                "kitchen_control_layer": "kitchen_control_layer.py",
                "fixed_cost": "fixed_cost_engine.py",
                "dre_engine": "dre_engine.py",
                "financial_truth_audit": "financial_truth_audit.py",
                "system_calibration": "system_calibration_engine.py",
                "executive_report": "executive_report_engine.py",
                "ceo_dashboard": "ceo_dashboard_engine.py",
                "sales_dashboard": "sales_dashboard_engine.py",
                "event_reconciliation": "event_reconciliation_engine.py"
            }
            
            engine_file = engine_map.get(step.tool, f"{step.tool}.py")
            
            if Path(ROOT_DIR / engine_file).exists():
                result = self.agent_dispatcher.dispatch(engine_file, step.inputs, context)
                step.outputs = result
            else:
                step.outputs = {
                    "status": "skipped",
                    "reason": f"Engine {engine_file} não encontrado"
                }
            
            step.completed_at = datetime.now().isoformat()
            
            # PASSO 8: Validar Resultado
            self._log("   Validando resultado...")
            is_valid, validation_msg = self.validator.validate_step_output(step)
            step.validation_result = validation_msg
            
            if not is_valid:
                self._log(f"   ❌ Validação falhou: {validation_msg}", "ERROR")
                step.status = "failed"
            else:
                self._log(f"   ✅ Step concluído")
                step.status = "completed"
        
        # PASSO 9: Registrar Logs e Memória
        self._log("PASSO 9/12: Registrando logs e memória...")
        run.logs.extend(self.log_buffer)
        self.memory_manager.persist_execution(run)
        
        # PASSO 10: Gerar Artifacts
        self._log("PASSO 10/12: Gerando artifacts...")
        
        # Coletar artefatos gerados pelos engines
        artifacts = []
        for step in run.steps:
            if step.status == "completed" and step.outputs:
                # Verificar se gerou arquivos
                if "artifacts" in step.outputs:
                    for art in step.outputs["artifacts"]:
                        artifacts.append(art)
        
        # Sempre gerar runtime_log
        log_file = RUNTIME_DIR / f"runtime_{run_id}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(self.log_buffer))
        
        run.artifacts = artifacts + [str(log_file)]
        
        # PASSO 11: Solicitar Approval se Necessário
        self._log("PASSO 11/12: Verificando necessidade de approval...")
        
        has_high_risk = any(s.risk_level.value >= RiskLevel.HIGH.value for s in run.steps)
        if has_high_risk:
            run.status = ExecutionStatus.APPROVAL_REQUIRED
            self._log("   ⚠️  Execução requer revisão (steps de alto risco)")
        else:
            run.status = ExecutionStatus.COMPLETED
        
        # PASSO 12: Encerrar Execução
        self._log("PASSO 12/12: Encerrando execução...")
        run.updated_at = datetime.now().isoformat()
        
        # Final
        self._log("="*80, "END")
        self._log(f"Execução {run_id} finalizada: {run.status.value}", "END")
        self._log(f"Total de steps: {len(run.steps)}")
        self._log(f"Steps concluídos: {sum(1 for s in run.steps if s.status == 'completed')}")
        self._log(f"Artifacts: {len(run.artifacts)}")
        self._log("="*80, "END")
        
        return run
    
    def get_run_status(self, run_id: str) -> Dict:
        """Retorna status de uma execução"""
        if run_id not in self.active_runs:
            return {"error": "Run not found"}
        
        run = self.active_runs[run_id]
        return {
            "run_id": run_id,
            "status": run.status.value,
            "workflow": run.workflow_type.name,
            "steps_total": len(run.steps),
            "steps_completed": sum(1 for s in run.steps if s.status == "completed"),
            "artifacts": len(run.artifacts),
            "created_at": run.created_at,
            "updated_at": run.updated_at
        }


def main():
    """Função principal - demonstração do runtime"""
    
    print("="*80)
    print("AGENT RUNTIME CORE v1.1")
    print("Orquestrador Central do Orkestra Finance Brain")
    print("="*80)
    print()
    print("Iniciando execução full pipeline...")
    print()
    
    # Criar runtime
    runtime = AgentRuntimeCore()
    
    # Input de exemplo
    input_data = {
        "action": "full_pipeline",
        "requester": "sistema",
        "params": {
            "generate_all": True,
            "validate": True
        }
    }
    
    # Executar
    run = runtime.execute_full_pipeline(input_data)
    
    # Status final
    print("\n" + "="*80)
    print("STATUS FINAL")
    print("="*80)
    print(f"Run ID: {run.run_id}")
    print(f"Status: {run.status.value}")
    print(f"Workflow: {run.workflow_type.name}")
    print(f"Steps: {len(run.steps)}")
    print(f"Artifacts: {len(run.artifacts)}")
    print(f"Log: runtime/RUNTIME_DIR/runtime_{run.run_id}.log")
    print("="*80)


if __name__ == "__main__":
    main()
