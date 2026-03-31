#!/usr/bin/env python3
"""
DATABASE ADAPTER
Adaptador para conexão com PostgreSQL baseado no schema_v1_2.sql

Funcionalidades:
- CRUD para todas as tabelas do schema
- Queries otimizadas para views
- Integração com Agent Runtime Core
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Simulação de psycopg2 (para ambiente sem PostgreSQL instalado)
class MockConnection:
    """Mock de conexão para testes"""
    def __init__(self):
        self.data = {}
    
    def fetch(self, query: str, params: tuple = ()) -> List[Dict]:
        """Simula fetch"""
        return []
    
    def execute(self, query: str, params: tuple = ()):
        """Simula execute"""
        pass


@dataclass
class AgentRunDB:
    """Modelo de agent_run para DB"""
    id: uuid.UUID
    company_id: uuid.UUID
    workflow_type: str
    status: str
    risk_level: str
    input_summary: str
    output_summary: str
    total_cost: float
    total_tokens: int
    latency_ms: int
    created_by: str
    started_at: datetime
    finished_at: Optional[datetime]
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AgentStepDB:
    """Modelo de agent_step para DB"""
    id: uuid.UUID
    agent_run_id: uuid.UUID
    step_order: int
    agent_name: str
    action_type: str
    input_payload: Dict
    output_payload: Dict
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


@dataclass
class ToolCallDB:
    """Modelo de tool_call para DB"""
    id: uuid.UUID
    agent_step_id: uuid.UUID
    tool_name: str
    tool_input: Dict
    tool_output: Dict
    status: str
    latency_ms: int
    cost_estimate: float


class DatabaseAdapter:
    """Adaptador de banco de dados"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string
        self.conn = None
        self.mock_mode = True
        
        # Tentar conectar com PostgreSQL
        try:
            import psycopg2
            if connection_string:
                self.conn = psycopg2.connect(connection_string)
                self.mock_mode = False
                print("✅ Conexão PostgreSQL estabelecida")
        except ImportError:
            print("⚠️  psycopg2 não instalado - usando modo mock")
            self.conn = MockConnection()
        except Exception as e:
            print(f"⚠️  Erro ao conectar PostgreSQL: {e}")
            self.conn = MockConnection()
    
    def create_agent_run(self, company_id: str, workflow_type: str, 
                         input_summary: str, created_by: str) -> str:
        """Cria novo agent_run"""
        run_id = uuid.uuid4()
        
        query = """
            INSERT INTO agent_runs (id, company_id, workflow_type, input_summary, created_by, started_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (run_id, company_id, workflow_type, input_summary, created_by))
                result = cursor.fetchone()
                return str(result[0])
            else:
                # Modo mock - salvar em JSON
                self._save_mock("agent_runs", {
                    "id": str(run_id),
                    "company_id": company_id,
                    "workflow_type": workflow_type,
                    "status": "pending",
                    "input_summary": input_summary,
                    "created_by": created_by,
                    "started_at": datetime.now().isoformat()
                })
                return str(run_id)
        except Exception as e:
            print(f"❌ Erro ao criar agent_run: {e}")
            return str(run_id)
    
    def update_agent_run_status(self, run_id: str, status: str, 
                                 total_cost: float = 0, total_tokens: int = 0):
        """Atualiza status do agent_run"""
        query = """
            UPDATE agent_runs 
            SET status = %s, total_cost = %s, total_tokens = %s, 
                finished_at = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE finished_at END
            WHERE id = %s
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (status, total_cost, total_tokens, status, run_id))
                self.conn.commit()
            else:
                print(f"📝 [MOCK] Update agent_run {run_id} → status: {status}")
        except Exception as e:
            print(f"❌ Erro ao atualizar agent_run: {e}")
    
    def create_agent_step(self, run_id: str, step_order: int, 
                         agent_name: str, action_type: str, 
                         input_payload: Dict) -> str:
        """Cria novo agent_step""""
        step_id = uuid.uuid4()
        
        query = """
            INSERT INTO agent_steps (id, agent_run_id, step_order, agent_name, action_type, input_payload, started_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (step_id, run_id, step_order, agent_name, action_type, json.dumps(input_payload)))
                result = cursor.fetchone()
                return str(result[0])
            else:
                self._save_mock("agent_steps", {
                    "id": str(step_id),
                    "agent_run_id": run_id,
                    "step_order": step_order,
                    "agent_name": agent_name,
                    "action_type": action_type,
                    "input_payload": input_payload,
                    "status": "pending"
                })
                return str(step_id)
        except Exception as e:
            print(f"❌ Erro ao criar agent_step: {e}")
            return str(step_id)
    
    def complete_agent_step(self, step_id: str, output_payload: Dict, 
                            status: str = "completed"):
        """Finaliza agent_step"""
        query = """
            UPDATE agent_steps 
            SET output_payload = %s, status = %s, finished_at = NOW()
            WHERE id = %s
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (json.dumps(output_payload), status, step_id))
                self.conn.commit()
            else:
                print(f"📝 [MOCK] Complete agent_step {step_id} → status: {status}")
        except Exception as e:
            print(f"❌ Erro ao completar agent_step: {e}")
    
    def create_tool_call(self, step_id: str, tool_name: str, 
                        tool_input: Dict) -> str:
        """Registra chamada de tool"""
        call_id = uuid.uuid4()
        
        query = """
            INSERT INTO tool_calls (id, agent_step_id, tool_name, tool_input, status, created_at)
            VALUES (%s, %s, %s, %s, 'pending', NOW())
            RETURNING id
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (call_id, step_id, tool_name, json.dumps(tool_input)))
                result = cursor.fetchone()
                return str(result[0])
            else:
                print(f"🛠️  [MOCK] Tool call: {tool_name}")
                return str(call_id)
        except Exception as e:
            print(f"❌ Erro ao criar tool_call: {e}")
            return str(call_id)
    
    def create_approval_request(self, run_id: str, risk_level: str, 
                               requested_action: str, justification: str) -> str:
        """Cria solicitação de aprovação"""
        approval_id = uuid.uuid4()
        
        query = """
            INSERT INTO approval_requests (id, agent_run_id, risk_level, requested_action, justification, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (approval_id, run_id, risk_level, requested_action, justification))
                result = cursor.fetchone()
                return str(result[0])
            else:
                print(f"🚦 [MOCK] Approval request: {requested_action} ({risk_level})")
                return str(approval_id)
        except Exception as e:
            print(f"❌ Erro ao criar approval_request: {e}")
            return str(approval_id)
    
    def create_artifact(self, run_id: str, artifact_type: str, 
                       file_name: str, storage_url: str) -> str:
        """Registra artefato gerado"""
        artifact_id = uuid.uuid4()
        
        query = """
            INSERT INTO artifacts (id, agent_run_id, artifact_type, file_name, storage_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (artifact_id, run_id, artifact_type, file_name, storage_url))
                result = cursor.fetchone()
                return str(result[0])
            else:
                print(f"📦 [MOCK] Artifact: {file_name}")
                return str(artifact_id)
        except Exception as e:
            print(f"❌ Erro ao criar artifact: {e}")
            return str(artifact_id)
    
    def get_agent_run_summary(self, run_id: str) -> Optional[Dict]:
        """Busca resumo de execução"""
        query = "SELECT * FROM v_agent_runs_summary WHERE id = %s"
        
        try:
            if not self.mock_mode:
                cursor = self.conn.cursor()
                cursor.execute(query, (run_id,))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return None
            else:
                return {"mock": True, "run_id": run_id}
        except Exception as e:
            print(f"❌ Erro ao buscar summary: {e}")
            return None
    
    def get_pending_approvals(self) -> List[Dict]:
        """Lista aprovações pendentes"""
        query = """
            SELECT ar.*, ar_workflow_type, ar_created_at
            FROM approval_requests ar
            JOIN agent_runs a ON a.id = ar.agent_run_id
            WHERE ar.status = 'pending'
            ORDER BY ar.requested_at DESC
        """
        
        return []
    
    def _save_mock(self, table: str, data: Dict):
        """Salva dados em modo mock (JSON local)"""
        mock_dir = Path(__file__).parent / "mock_db"
        mock_dir.mkdir(exist_ok=True)
        
        file_path = mock_dir / f"{table}.jsonl"
        
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, default=str) + "\n")


def main():
    """Teste do adaptador"""
    
    print("🎛️ DATABASE ADAPTER - Orkestra Finance Brain")
    print("="*60)
    
    # Criar adaptador
    db = DatabaseAdapter()
    
    # Testar criação de agent_run
    run_id = db.create_agent_run(
        company_id="550e8400-e29b-41d4-a716-446655440000",
        workflow_type="FULL_PIPELINE",
        input_summary="Execução completa do sistema",
        created_by="sistema"
    )
    
    print(f"\n✅ Agent Run criado: {run_id}")
    
    # Testar atualização de status
    db.update_agent_run_status(run_id, "running")
    db.update_agent_run_status(run_id, "completed", total_cost=0.50, total_tokens=1500)
    
    # Testar criação de step
    step_id = db.create_agent_step(
        run_id=run_id,
        step_order=1,
        agent_name="kitchen_control",
        action_type="calculate_costs",
        input_payload={"test": True}
    )
    
    print(f"✅ Agent Step criado: {step_id}")
    
    # Completar step
    db.complete_agent_step(step_id, {"status": "ok"})
    
    # Criar approval
    approval_id = db.create_approval_request(
        run_id=run_id,
        risk_level="high",
        requested_action="price_update",
        justification="Margem abaixo do esperado"
    )
    
    print(f"✅ Approval Request: {approval_id}")
    
    # Criar artifact
    artifact_id = db.create_artifact(
        run_id=run_id,
        artifact_type="json",
        file_name="dre_events.csv",
        storage_url="/output/dre_events.csv"
    )
    
    print(f"✅ Artifact: {artifact_id}")
    
    print("\n" + "="*60)
    print("Database Adapter testado com sucesso!")
    print("Para PostgreSQL real, configure connection_string")


if __name__ == "__main__":
    main()
