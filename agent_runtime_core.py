#!/usr/bin/env python3
"""
🎛️ AGENT RUNTIME CORE v1.1
Orquestrador central do Orkestra Finance Brain

12 passos de orquestração com Policy Engine.
"""

import json
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

# ============================================================
# CONFIGURAÇÃO
# ============================================================

class RiskLevel(str, Enum):
    R0_READ_ONLY = "R0"
    R1_SAFE_WRITE = "R1"
    R2_EXTERNAL_EFFECT = "R2"
    R3_FINANCIAL = "R3"
    R4_DESTRUCTIVE = "R4"
    R5_CRITICAL = "R5"

class PolicyDecision(str, Enum):
    AUTO_EXECUTE = "AUTO_EXECUTE"
    LOG_ONLY = "LOG_ONLY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"

# ============================================================
# MODELS
# ============================================================

@dataclass
class AgentRun:
    id: str
    company_id: str
    workflow_type: str
    status: str = "pending"
    risk_level: str = "low"
    input_summary: str = ""
    output_summary: str = ""
    total_cost: float = 0.0
    total_tokens: int = 0
    latency_ms: int = 0
    created_by: str = "system"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    steps: List[Dict] = field(default_factory=list)
    approvals: List[Dict] = field(default_factory=list)

@dataclass
class PolicyCheck:
    risk_level: RiskLevel
    confidence_threshold: float
    requires_approval: bool
    auto_execute: bool

# ============================================================
# POLICY ENGINE
# ============================================================

class PolicyEngine:
    """Motor de políticas para classificação de risco"""
    
    def evaluate(self, action_type: str, context: Dict) -> PolicyDecision:
        """Avalia risco baseado no tipo de ação"""
        
        # Alta confiança e baixo risco → auto-execute
        if action_type in ["calculation", "query", "read"]:
            return PolicyDecision.AUTO_EXECUTE
        
        # Escrita segura → log mas executa
        if action_type in ["log", "cache", "update_cache"]:
            return PolicyDecision.LOG_ONLY
        
        # Impacto externo → requer aprovação de humano
        if action_type in ["send_email", "send_invoice", "payment"]:
            return PolicyDecision.APPROVAL_REQUIRED
        
        # Destrutivo ou irreversível → human-in-the-loop obrigatório
        if action_type in ["delete", "cancel_event", "refund"]:
            return PolicyDecision.BLOCKED
        
        return PolicyDecision.APPROVAL_REQUIRED

# ============================================================
# MEMORY MANAGER
# ============================================================

class MemoryManager:
    """Gerencia memória de contexto"""
    
    def __init__(self, company_id: str):
        self.company_id = company_id
        self.memories: List[Dict] = []
    
    def add(self, memory_type: str, content: str, confidence: float = 1.0):
        """Adiciona nova memória"""
        self.memories.append({
            "id": str(uuid.uuid4()),
            "type": memory_type,
            "content": content,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca memória por similaridade (simplificado)"""
        return [m for m in self.memories if query.lower() in m["content"].lower()][:limit]
    
    def get_by_type(self, memory_type: str) -> List[Dict]:
        """Retorna memórias por tipo"""
        return [m for m in self.memories if m["type"] == memory_type]

# ============================================================
# ARTIFACT MANAGER
# ============================================================

class ArtifactManager:
    """Gerencia artefatos gerados"""
    
    def __init__(self, artifacts_dir: str = "./artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(exist_ok=True)
    
    def save(self, agent_run_id: str, name: str, data: Any, format: str = "json") -> str:
        """Salva artefato em disco"""
        artifact_id = f"{agent_run_id}_{name}.{format}"
        path = self.artifacts_dir / artifact_id
        
        if format == "json":
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(path, 'w') as f:
                f.write(str(data))
        
        return str(path)
    
    def load(self, artifact_id: str) -> Any:
        """Carrega artefato"""
        path = self.artifacts_dir / artifact_id
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

# ============================================================
# RUNTIME CORE - 12 PASSOS
# ============================================================

class AgentRuntimeCore:
    """
    Orquestrador central com 12 passos:
    
    1. Task Intake       - Recebe e normaliza input
    2. Classification    - Classifica tipo de workflow
    3. Memory Load       - Carrega contexto mínimo
    4. Policy Check      - Verifica risco/permissões
    5. Planning          - Cria plano de execução
    6. Routing           - Roteia para engines
    7. Validation        - Valida dados antes de executar
    8. Execution         - Executa engines Python
    9. Quality Check     - Valida outputs
    10. Memory Write     - Persiste aprendizados
    11. Artifact Gen     - Gera artefatos
    12. Response Format  - Formata resposta final
    """
    
    def __init__(self, company_id: str = "default"):
        self.company_id = company_id
        self.policy_engine = PolicyEngine()
        self.memory = MemoryManager(company_id)
        self.artifacts = ArtifactManager()
        self.status: Dict[str, Any] = {}
    
    def run(self, input_data: Dict) -> Dict:
        """Executa pipeline completo de 12 passos"""
        
        print("="*70)
        print("🎛️ AGENT RUNTIME CORE v1.1")
        print("="*70)
        
        try:
            # PASSO 1: Task Intake
            self._step_1_task_intake(input_data)
            
            # PASSO 2: Classification
            self._step_2_classification()
            
            # PASSO 3: Memory Load
            self._step_3_memory_load()
            
            # PASSO 4: Policy Check
            self._step_4_policy_check()
            
            # PASSO 5: Planning
            self._step_5_planning()
            
            # PASSO 6: Routing
            self._step_6_routing()
            
            # PASSO 7: Validation
            self._step_7_validation()
            
            # PASSO 8: Execution
            self._step_8_execution()
            
            # PASSO 9: Quality Check
            self._step_9_quality_check()
            
            # PASSO 10: Memory Write
            self._step_10_memory_write()
            
            # PASSO 11: Artifact Generation
            self._step_11_artifact_generation()
            
            # PASSO 12: Response Formatting
            return self._step_12_response_format()
            
        except Exception as e:
            print(f"\n❌ ERRO NO RUNTIME: {str(e)}")
            return self._handle_error(e)
    
    def _step_1_task_intake(self, input_data: Dict):
        """1. Recebe e normaliza input"""
        print("[STEP 1/12] Task Intake - Normalizando input...")
        
        self.run_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.input_data = input_data
        
        # Cria registro do agent run
        self.agent_run = AgentRun(
            id=self.run_id,
            company_id=self.company_id,
            workflow_type=input_data.get("workflow_type", "unknown"),
            status="running",
            input_summary=str(input_data)[:200]
        )
        
        print(f"    ✓ Run ID: {self.run_id}")
        print(f"    ✓ Workflow: {self.agent_run.workflow_type}")
        self._add_step("task_intake", "completed")
    
    def _step_2_classification(self):
        """2. Classifica tipo de workflow"""
        print("[STEP 2/12] Classification - Identificando workflow...")
        
        workflow = self.input_data.get("workflow_type", "FULL_PIPELINE")
        self.workflow_config = {
            "KITCHEN": ["kitchen_control_layer.py"],
            "DRE": ["dre_engine.py"],
            "AUDIT": ["financial_truth_audit.py"],
            "FULL_PIPELINE": [
                "kitchen_control_layer.py",
                "fixed_cost_engine.py",
                "dre_engine.py",
                "margin_validation_engine.py",
                "financial_truth_audit.py",
                "executive_report_engine.py",
                "ceo_dashboard_engine.py"
            ]
        }.get(workflow, [])
        
        print(f"    ✓ Workflow: {workflow}")
        print(f"    ✓ Engines: {len(self.workflow_config)}")
        self._add_step("classification", "completed", {"engines": len(self.workflow_config)})
    
    def _step_3_memory_load(self):
        """3. Carrega contexto mínimo"""
        print("[STEP 3/12] Memory Load - Carregando contexto...")
        
        # Carrega memórias relevantes
        context_memories = self.memory.get_by_type("pricing_insight")
        
        self.context = {
            "relevant_memories": len(context_memories),
            "last_successful_run": None,
            "company_rules": []
        }
        
        print(f"    ✓ Contexto carregado: {len(context_memories)} memórias")
        self._add_step("memory_load", "completed", {"memories": len(context_memories)})
    
    def _step_4_policy_check(self):
        """4. Verifica risco e permissões"""
        print("[STEP 4/12] Policy Check - Verificando permissões...")
        
        action_type = self.input_data.get("action_type", "calculation")
        decision = self.policy_engine.evaluate(action_type, self.context)
        
        self.policy_decision = decision
        
        if decision == PolicyDecision.BLOCKED:
            raise PermissionError(f"Ação '{action_type}' bloqueada pela política")
        
        print(f"    ✓ Decision: {decision.value}")
        print(f"    ✓ Action: {action_type}")
        self._add_step("policy_check", "completed", {"decision": decision.value})
    
    def _step_5_planning(self):
        """5. Cria plano de execução"""
        print("[STEP 5/12] Planning - Criando plano...")
        
        self.execution_plan = {
            "engines": self.workflow_config,
            "parallel": False,
            "retries": 3,
            "checkpoint_interval": 1
        }
        
        print(f"    ✓ Plano: {len(self.workflow_config)} engines")
        self._add_step("planning", "completed", {"engines": len(self.workflow_config)})
    
    def _step_6_routing(self):
        """6. Roteia para engines"""
        print("[STEP 6/12] Routing - Roteando engines...")
        
        self.engines_results = []
        
        for engine in self.workflow_config:
            print(f"    → Roteando: {engine}")
            self.engines_results.append({
                "engine": engine,
                "status": "routed",
                "ready": True
            })
        
        self._add_step("routing", "completed", {"routed": len(self.engines_results)})
    
    def _step_7_validation(self):
        """7. Valida dados"""
        print("[STEP 7/12] Validation - Validando dados...")
        
        # Validações básicas
        validations = [
            ("input_present", bool(self.input_data)),
            ("company_id_valid", bool(self.company_id)),
            ("engines_configured", len(self.workflow_config) > 0)
        ]
        
        failed = [name for name, passed in validations if not passed]
        
        if failed:
            raise ValueError(f"Validações falharam: {failed}")
        
        print(f"    ✓ {len(validations)} validações OK")
        self._add_step("validation", "completed", {"checks": len(validations)})
    
    def _step_8_execution(self):
        """8. Executa engines Python"""
        print("[STEP 8/12] Execution - Executando engines...")
        
        results = []
        
        for engine in self.workflow_config:
            if engine.endswith('.py'):
                try:
                    # Executa engine Python
                    result = subprocess.run(
                        ['python3', engine],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    success = result.returncode == 0
                    results.append({
                        "engine": engine,
                        "success": success,
                        "output": result.stdout if success else result.stderr
                    })
                    
                    status = "✓" if success else "✗"
                    print(f"    {status} {engine}")
                    
                except Exception as e:
                    results.append({
                        "engine": engine,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"    ✗ {engine}: {e}")
        
        self.execution_results = results
        self._add_step("execution", "completed", {"engines": len(results)})
    
    def _step_9_quality_check(self):
        """9. Valida outputs"""
        print("[STEP 9/12] Quality Check - Validando qualidade...")
        
        success_count = sum(1 for r in self.execution_results if r.get("success"))
        total = len(self.execution_results)
        
        self.quality_score = success_count / total if total > 0 else 0
        
        print(f"    ✓ Score: {self.quality_score:.1%}")
        print(f"    ✓ Success: {success_count}/{total}")
        
        self._add_step("quality_check", "completed", {"score": self.quality_score})
    
    def _step_10_memory_write(self):
        """10. Persiste aprendizados"""
        print("[STEP 10/12] Memory Write - Persistindo aprendizados...")
        
        # Adiciona memória da execução
        self.memory.add(
            memory_type="execution_result",
            content=f"Run {self.run_id}: {self.quality_score:.0%} sucesso",
            confidence=self.quality_score
        )
        
        print(f"    ✓ Memória persistida: {len(self.memory.memories)} total")
        self._add_step("memory_write", "completed")
    
    def _step_11_artifact_generation(self):
        """11. Gera artefatos"""
        print("[STEP 11/12] Artifact Generation - Gerando artefatos...")
        
        artifact_paths = []
        
        # Gera resumo do runtime
        summary = {
            "run_id": self.run_id,
            "workflow": self.agent_run.workflow_type,
            "quality_score": self.quality_score,
            "steps": self.agent_run.steps,
            "execution_results": self.execution_results
        }
        
        path = self.artifacts.save(self.run_id, "runtime_summary", summary)
        artifact_paths.append(path)
        
        print(f"    ✓ Artefatos: {len(artifact_paths)}")
        self._add_step("artifact_generation", "completed", {"artifacts": len(artifact_paths)})
    
    def _step_12_response_format(self) -> Dict:
        """12. Formata resposta final"""
        print("[STEP 12/12] Response Format - Formatando resposta...")
        
        # Calcula métricas
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        self.agent_run.finished_at = datetime.now().isoformat()
        self.agent_run.latency_ms = elapsed_ms
        self.agent_run.status = "completed" if self.quality_score >= 0.8 else "completed_with_warnings"
        
        response = {
            "success": True,
            "run_id": self.run_id,
            "company_id": self.company_id,
            "workflow_type": self.agent_run.workflow_type,
            "status": self.agent_run.status,
            "quality_score": self.quality_score,
            "latency_ms": elapsed_ms,
            "policy_decision": self.policy_decision.value,
            "steps_completed": len(self.agent_run.steps),
            "engines_executed": len(self.execution_results),
            "memories_created": len(self.memory.memories),
            "created_at": self.agent_run.created_at,
            "finished_at": self.agent_run.finished_at
        }
        
        self._save_runtime_log(response)
        
        print("="*70)
        print(f"🎉 RUNTIME COMPLETADO em {elapsed_ms}ms")
        print(f"   Qualidade: {self.quality_score:.1%} | Steps: {len(self.agent_run.steps)}")
        print("="*70)
        
        return response
    
    def _add_step(self, name: str, status: str, metadata: Dict = None):
        """Adiciona passo ao registro"""
        self.agent_run.steps.append({
            "name": name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
    
    def _handle_error(self, error: Exception) -> Dict:
        """Trata erros do runtime"""
        self.agent_run.status = "failed"
        self.agent_run.output_summary = str(error)
        
        return {
            "success": False,
            "error": str(error),
            "run_id": getattr(self, 'run_id', 'unknown'),
            "step": self.agent_run.steps[-1] if self.agent_run.steps else None
        }
    
    def _save_runtime_log(self, response: Dict):
        """Salva log do runtime"""
        log_dir = Path("./runtime")
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"run_{self.run_id}.json"
        with open(log_file, 'w') as f:
            json.dump({
                "agent_run": asdict(self.agent_run),
                "response": response,
                "execution_results": getattr(self, 'execution_results', []),
                "memory": self.memory.memories
            }, f, indent=2, default=str)
        
        print(f"   💾 Log salvo: {log_file}")

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys
    
    # Configura input padrão
    input_data = {
        "company_id": "opera",
        "workflow_type": "FULL_PIPELINE",
        "action_type": "calculation",
        "context": {
            "reference_month": "2024-03"
        }
    }
    
    # Permite override via argumentos
    if len(sys.argv) > 1:
        try:
            input_data = json.loads(sys.argv[1])
        except json.JSONDecodeError:
            print(f"⚠️ JSON inválido, usando padrão")
    
    # Executa runtime
    runtime = AgentRuntimeCore(company_id=input_data.get("company_id", "opera"))
    result = runtime.run(input_data)
    
    # Output JSON
    print("\n" + "="*70)
    print("📊 RESULTADO:")
    print("="*70)
    print(json.dumps(result, indent=2, default=str))
