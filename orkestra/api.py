# api.py - Orkestra FastAPI REST API
# API REST para integração externa

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import sys
import subprocess

# Configurar path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "engine"))
sys.path.insert(0, str(BASE_DIR.parent))  # Scripts

app = FastAPI(
    title="Orkestra API",
    description="API REST para Sistema de Gestão de Eventos",
    version="1.0.0"
)

# ============================================
# MODELOS Pydantic
# ============================================

class Transaction(BaseModel):
    type: str = Field(..., description="Tipo: income ou expense")
    value: float = Field(..., gt=0, description="Valor em centavos")
    category: str = Field(..., description="Categoria do item")
    event: str = Field(..., description="Nome do evento")
    has_alerts: bool = Field(default=False)


class EventInput(BaseModel):
    name: str = Field(..., description="Nome do evento")
    revenue: float = Field(..., gt=0, description="Receita esperada")
    cost: float = Field(..., gt=0, description="Custo estimado")
    capacity: Optional[int] = Field(default=100, description="Número de pessoas")
    complexity: Optional[str] = Field(default="medium", description="baixa/media/alta")


class EventResult(BaseModel):
    name: str
    revenue: float
    cost: float
    margin: float
    decision: str
    rationale: str


class DecisionRecord(BaseModel):
    id: str
    timestamp: str
    event: str
    margin: float
    margin_before: float
    issue: str
    cause: str
    action: str
    result: str
    notes: str


class SystemStatus(BaseModel):
    status: str
    decisions_count: int
    errors_count: int
    performance_count: int
    uptime: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str


# ============================================
# ENDPOINTS
# ============================================

@app.get("/", response_model=HealthResponse, tags=["Health"])
def root():
    """Endpoint raiz - verifica se API está online."""
    return {
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check da API."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/status", response_model=SystemStatus, tags=["Status"])
def get_status():
    """Retorna status completo do sistema."""
    try:
        # Carregar dados de memória
        mem_dir = BASE_DIR / "memory"
        
        decisions_data = json.loads((mem_dir / "decisions.json").read_text()) if (mem_dir / "decisions.json").exists() else {}
        errors_data = json.loads((mem_dir / "errors.json").read_text()) if (mem_dir / "errors.json").exists() else {}
        perf_data = json.loads((mem_dir / "performance.json").read_text()) if (mem_dir / "performance.json").exists() else {}
        
        return {
            "status": "operational",
            "decisions_count": len(decisions_data.get("decisions", [])),
            "errors_count": len(errors_data.get("errors", [])),
            "performance_count": len(perf_data.get("records", [])),
            "uptime": "running"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate", response_model=EventResult, tags=["Events"])
def evaluate_event_api(event: EventInput):
    """
    Avalia viabilidade de um evento.
    Retorna decisão: APPROVE, REVIEW ou REJECT.
    """
    margin = (event.revenue - event.cost) / event.revenue if event.revenue > 0 else 0
    
    event_data = {
        "name": event.name,
        "revenue": event.revenue,
        "cost": event.cost,
        "margin": margin,
        "complexity": event.complexity,
        "capacity": event.capacity
    }
    
    # Importar evaluator
    try:
        from agents.evaluator_simple import evaluate_event, evaluate_event_detailed
        decision = evaluate_event(event_data)
        detailed = evaluate_event_detailed(event_data)
    except:
        # Fallback simples
        if margin < 0:
            decision = "REJECT"
            rationale = "Margem negativa - evento inviável"
        elif margin < 0.3:
            decision = "REVIEW"
            rationale = "Margem abaixo do ideal (30%)"
        else:
            decision = "APPROVE"
            rationale = "Margem saudável"
        
        detailed = {"rationale": rationale}
    
    return {
        "name": event.name,
        "revenue": event.revenue,
        "cost": event.cost,
        "margin": margin,
        "decision": decision,
        "rationale": detailed.get("rationale", "")
    }


@app.post("/analyze", response_model=List[EventResult], tags=["Analysis"])
def analyze_financial_data(data: List[Transaction]):
    """
    Analisa lista de transações financeiras.
    Retorna análise por evento.
    """
    # Agrupar por evento
    events = {}
    for t in data:
        if t.event not in events:
            events[t.event] = {"revenue": 0, "cost": 0}
        
        if t.type == "income":
            events[t.event]["revenue"] += t.value
        else:
            events[t.event]["cost"] += t.value
    
    results = []
    for name, values in events.items():
        revenue = values["revenue"]
        cost = values["cost"]
        margin = (revenue - cost) / revenue if revenue > 0 else 0
        
        event_data = {
            "name": name,
            "revenue": revenue,
            "cost": cost,
            "margin": margin
        }
        
        try:
            from agents.evaluator_simple import evaluate_event, evaluate_event_detailed
            decision = evaluate_event(event_data)
            detailed = evaluate_event_detailed(event_data)
        except:
            decision = "REVIEW" if margin < 0.3 else "APPROVE"
            detailed = {"rationale": "Análise padrão"}
        
        results.append({
            "name": name,
            "revenue": revenue,
            "cost": cost,
            "margin": margin,
            "decision": decision,
            "rationale": detailed.get("rationale", "")
        })
    
    return results


@app.post("/decisions", response_model=DecisionRecord, tags=["Memory"])
def create_decision(
    event: str = Body(...),
    margin: float = Body(...),
    margin_before: float = Body(0),
    issue: str = Body(""),
    cause: str = Body(""),
    action: str = Body(""),
    result: str = Body(""),
    notes: str = Body("")
):
    """Registra uma nova decisão na memória."""
    try:
        sys.path.insert(0, str(BASE_DIR.parent))
        from scripts.memory_manager import memory
        
        decision_id = memory.add_decision(
            event=event,
            margin=margin,
            margin_before=margin_before,
            issue=issue,
            cause=cause,
            action=action,
            result=result,
            notes=notes
        )
        
        return {
            "id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "margin": margin,
            "margin_before": margin_before,
            "issue": issue,
            "cause": cause,
            "action": action,
            "result": result,
            "notes": notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decisions", response_model=List[DecisionRecord], tags=["Memory"])
def get_decisions(limit: int = Query(50, ge=1, le=100)):
    """Retorna histórico de decisões."""
    try:
        mem_file = BASE_DIR / "memory" / "decisions.json"
        if not mem_file.exists():
            return []
        
        data = json.loads(mem_file.read_text())
        decisions = data.get("decisions", [])[:limit]
        return decisions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/learning", response_model=Dict[str, Any], tags=["Learning"])
def run_learning():
    """Executa Learning Engine e retorna insights."""
    try:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "engine" / "learning_engine.py")],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Carregar relatório gerado
        report_file = BASE_DIR / "memory" / "learning_report.json"
        if report_file.exists():
            report = json.loads(report_file.read_text())
            return {
                "status": "success",
                "insights_count": report.get("insights_count", 0),
                "rules_count": report.get("rules_count", 0),
                "insights": report.get("insights", []),
                "rules": report.get("rules", [])
            }
        
        return {"status": "completed", "message": "Learning engine executado"}
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Learning Engine timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline", response_model=Dict[str, Any], tags=["Pipeline"])
def run_pipeline():
    """Executa pipeline completo do Orkestra."""
    try:
        result = subprocess.run(
            ["python3", str(BASE_DIR / "engine" / "orchestrator.py")],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Carregar relatório
        report_file = BASE_DIR / "memory" / "pipeline_report.json"
        if report_file.exists():
            report = json.loads(report_file.read_text())
            return {
                "status": "success",
                "summary": report.get("summary", {}),
                "events_analyzed": report.get("summary", {}).get("events_analyzed", 0),
                "avg_margin": report.get("summary", {}).get("avg_margin", 0)
            }
        
        return {"status": "completed", "output": result.stdout}
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Pipeline timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
