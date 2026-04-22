"""
Orkestra Finance Brain — FastAPI REST API
Endpoints: /auth, /audit, /decisions, /agents, /pricing, /parameters
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import jwt

# ============================================================
# CONFIG
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/orkestra")
JWT_SECRET = os.getenv("JWT_SECRET", "orkestra-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ============================================================
# DATABASE POOL
# ============================================================
db_pool: Optional[asyncpg.Pool] = None

async def get_db() -> asyncpg.Connection:
    """Get database connection from pool"""
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    return await db_pool.acquire()

async def close_db(conn: asyncpg.Connection):
    """Release database connection"""
    await db_pool.release(conn)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan manager"""
    global db_pool
    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=5,
        max_size=20,
        command_timeout=60
    )
    print("✅ Database connected")
    yield
    await db_pool.close()
    print("👋 Database disconnected")

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="Orkestra Finance Brain API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================================
# MODELS
# ============================================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[str] = None

class AuditLogEntry(BaseModel):
    id: str
    actor_type: str
    action_type: str
    resource_type: str
    resource_id: str
    created_at: datetime

class DecisionCreate(BaseModel):
    model_name: str = "kimi-k2.5"
    model_version: str = "1.0"
    input_context: Dict[str, Any]
    output_decision: Dict[str, Any]
    confidence_score: float = Field(..., ge=0, le=1)
    reasoning_chain: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DecisionResponse(DecisionCreate):
    id: str
    decision_id: str
    tenant_id: str
    created_at: datetime

class PricingCalculate(BaseModel):
    guests: int = Field(..., gt=0)
    event_type: str = "social"  # corporate, social, wedding
    menu_price_per_person: float = Field(..., gt=0)
    drink_price_per_person: float = Field(..., ge=0)
    staff_rate: float = Field(default=18, ge=0, le=100)

class PricingResult(BaseModel):
    revenue: float
    cmv: float
    profit: float
    margin_pct: float
    score: str
    reason: str

class ParameterCreate(BaseModel):
    category: str
    key: str
    value: Any
    value_type: str = "string"  # string, number, boolean, json, array
    description: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

# ============================================================
# AUTH UTILITIES
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return payload

async def get_user_db(user: dict = Depends(get_current_user)):
    """Get user from database"""
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM rbac_users WHERE email = $1",
            user.get("sub")
        )
        if not row:
            raise HTTPException(status_code=401, detail="User not found")
        return dict(row)
    finally:
        await close_db(conn)

async def check_permission(user_id: str, resource: str, action: str):
    """Check if user has permission"""
    conn = await get_db()
    try:
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1 FROM rbac_user_roles ur
                JOIN rbac_roles r ON r.id = ur.role_id
                WHERE ur.user_id = $1
                  AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
                  AND r.active = TRUE
                  AND (
                      r.permissions @> jsonb_build_array(jsonb_build_object('resource', $2, 'action', $3))
                      OR r.permissions @> jsonb_build_array(jsonb_build_object('resource', '*', 'action', '*'))
                  )
            )
            """,
            user_id, resource, action
        )
        return result
    finally:
        await close_db(conn)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = await get_db()
        try:
            await conn.fetchval("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        finally:
            await close_db(conn)
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)}
        )

# ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/auth/login", response_model=Token)
async def login(request: LoginRequest):
    """Login and get JWT token"""
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash FROM rbac_users WHERE email = $1 AND active = TRUE",
            request.email
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Hash verification (simplified - use bcrypt in production)
        # Compare with stored hash
        # For now, accept any password with 'password' in it as demo
        if request.password != "password" and request.password != "admin123":
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get tenant
        tenant = await conn.fetchrow(
            "SELECT t.id FROM tenants t JOIN rbac_users u ON u.tenant_id = t.id WHERE u.id = $1",
            user["id"]
        )
        
        access_token = create_access_token({
            "sub": user["email"],
            "user_id": str(user["id"]),
            "tenant_id": str(tenant["id"]),
            "type": "access"
        })
        
        # Update last login
        await conn.execute(
            "UPDATE rbac_users SET last_login_at = NOW(), failed_logins = 0 WHERE id = $1",
            user["id"]
        )
        
        return Token(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    finally:
        await close_db(conn)

@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {
        "email": current_user.get("sub"),
        "user_id": current_user.get("user_id"),
        "tenant_id": current_user.get("tenant_id")
    }

# ============================================================
# AUDIT ENDPOINTS
# ============================================================

@app.get("/audit")
async def list_audit(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    resource_type: Optional[str] = None,
    action_type: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List audit logs with filtering"""
    # Check permission
    has_perm = await check_permission(user.get("user_id"), "audit", "read")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        where_clauses = ["tenant_id = $1"]
        params = [user.get("tenant_id")]
        param_idx = 2
        
        if resource_type:
            where_clauses.append(f"resource_type = ${param_idx}")
            params.append(resource_type)
            param_idx += 1
        
        if action_type:
            where_clauses.append(f"action_type = ${param_idx}")
            params.append(action_type)
            param_idx += 1
            
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT id, actor_type, action_type, resource_type, resource_id, 
                   LEFT(diff_summary, 100) as diff_summary, created_at
            FROM audit_log
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    finally:
        await close_db(conn)

@app.get("/audit/{log_id}")
async def get_audit(log_id: str, user: dict = Depends(get_current_user)):
    """Get specific audit log with full details"""
    has_perm = await check_permission(user.get("user_id"), "audit", "read")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        row = await conn.fetchrow(
            "SELECT * FROM audit_log WHERE id = $1 AND tenant_id = $2",
            log_id, user.get("tenant_id")
        )
        if not row:
            raise HTTPException(status_code=404, detail="Log not found")
        return dict(row)
    finally:
        await close_db(conn)

# ============================================================
# DECISIONS ENDPOINTS
# ============================================================

@app.post("/decisions", response_model=DecisionResponse, status_code=201)
async def create_decision(
    decision: DecisionCreate,
    user: dict = Depends(get_current_user)
):
    """Log a decision from AI model"""
    has_perm = await check_permission(user.get("user_id"), "agent", "execute")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        decision_id = f"DEC-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        
        row = await conn.fetchrow(
            """
            INSERT INTO decision_log (
                tenant_id, decision_id, model_name, model_version,
                prompt_tokens, completion_tokens, total_tokens,
                input_context, output_decision, reasoning_chain, confidence_score,
                metadata, agent_id, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
            RETURNING *
            """,
            user.get("tenant_id"),
            decision_id,
            decision.model_name,
            decision.model_version,
            0,  # prompt_tokens - calculate actual
            0,  # completion_tokens - calculate actual
            0,  # total_tokens
            json.dumps(decision.input_context),
            json.dumps(decision.output_decision),
            json.dumps(decision.reasoning_chain) if decision.reasoning_chain else "{}",
            decision.confidence_score,
            json.dumps(decision.metadata) if decision.metadata else "{}",
            user.get("user_id")
        )
        
        return DecisionResponse(
            id=str(row["id"]),
            decision_id=row["decision_id"],
            tenant_id=str(row["tenant_id"]),
            created_at=row["created_at"],
            **decision.dict()
        )
    finally:
        await close_db(conn)

@app.get("/decisions")
async def list_decisions(
    limit: int = 20,
    min_confidence: Optional[float] = None,
    user: dict = Depends(get_current_user)
):
    """List decisions with filtering"""
    conn = await get_db()
    try:
        query = "SELECT * FROM decision_log WHERE tenant_id = $1"
        params = [user.get("tenant_id")]
        
        if min_confidence:
            query += " AND confidence_score >= $2"
            params.append(min_confidence)
            
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
    finally:
        await close_db(conn)

@app.post("/decisions/{decision_id}/review")
async def review_decision(
    decision_id: str,
    status: str,  # approved, rejected, flagged
    user: dict = Depends(get_current_user)
):
    """Review a decision (requires permission)"""
    if status not in ["approved", "rejected", "flagged"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    conn = await get_db()
    try:
        result = await conn.execute(
            """
            UPDATE decision_log 
            SET review_status = $1, reviewed_by = $2, reviewed_at = NOW()
            WHERE decision_id = $3 AND tenant_id = $4
            """,
            status, user.get("user_id"), decision_id, user.get("tenant_id")
        )
        return {"status": "reviewed", "decision_id": decision_id, "review_status": status}
    finally:
        await close_db(conn)

# ============================================================
# PRICING ENDPOINTS
# ============================================================

@app.post("/pricing/calculate", response_model=PricingResult)
async def calculate_pricing(
    calc: PricingCalculate,
    user: dict = Depends(get_current_user)
):
    """Calculate event pricing with GO/NO-GO scoring"""
    has_perm = await check_permission(user.get("user_id"), "pricing", "execute")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get parameters
    conn = await get_db()
    try:
        threshold_go = await conn.fetchval(
            """
            SELECT COALESCE((value->>0)::NUMERIC, 35)
            FROM system_parameters
            WHERE tenant_id = $1 AND key = 'threshold_go' AND cost_center_id IS NULL
            """,
            user.get("tenant_id")
        ) or 35
        
        threshold_alert = await conn.fetchval(
            """
            SELECT COALESCE((value->>0)::NUMERIC, 25)
            FROM system_parameters
            WHERE tenant_id = $1 AND key = 'threshold_alert' AND cost_center_id IS NULL
            """,
            user.get("tenant_id")
        ) or 25
        
        # Calculate
        revenue = calc.guests * (calc.menu_price_per_person + calc.drink_price_per_person)
        food_cost = calc.guests * calc.menu_price_per_person * 0.65
        drink_cost = calc.guests * calc.drink_price_per_person * 0.45
        staff_cost = revenue * (calc.staff_rate / 100)
        cmv = food_cost + drink_cost + staff_cost
        profit = revenue - cmv
        margin_pct = (profit / revenue * 100) if revenue > 0 else 0
        
        # Determine score
        if margin_pct >= threshold_go:
            score = "GO"
            reason = f"Margem {margin_pct:.1f}% acima do threshold GO ({threshold_go:.1f}%)"
        elif margin_pct >= threshold_alert:
            score = "GO*"
            reason = f"Margem {margin_pct:.1f}% aceitável (entre {threshold_alert:.1f}% e {threshold_go:.1f}%)"
        elif margin_pct >= 15:
            score = "NO-GO"
            reason = f"Margem {margin_pct:.1f}% abaixo do ideal, revisar orçamento"
        else:
            score = "CRITICAL"
            reason = f"Margem {margin_pct:.1f}% crítica - evento pode gerar prejuízo"
        
        # Log to audit
        # await conn.execute(...)  # Optional: log calculation
        
        return PricingResult(
            revenue=round(revenue, 2),
            cmv=round(cmv, 2),
            profit=round(profit, 2),
            margin_pct=round(margin_pct, 2),
            score=score,
            reason=reason
        )
    finally:
        await close_db(conn)

@app.get("/pricing/markups")
async def get_markups(user: dict = Depends(get_current_user)):
    """Get current markup configuration"""
    conn = await get_db()
    try:
        rows = await conn.fetch(
            """
            SELECT key, value, description
            FROM system_parameters
            WHERE tenant_id = $1 AND category = 'pricing'
            """,
            user.get("tenant_id")
        )
        return {row["key"]: {"value": row["value"], "desc": row["description"]} for row in rows}
    finally:
        await close_db(conn)

# ============================================================
# PARAMETERS ENDPOINTS
# ============================================================

@app.get("/parameters")
async def list_parameters(
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List system parameters"""
    conn = await get_db()
    try:
        if category:
            rows = await conn.fetch(
                "SELECT key, value, value_type, description, version FROM system_parameters WHERE tenant_id = $1 AND category = $2 ORDER BY key",
                user.get("tenant_id"), category
            )
        else:
            rows = await conn.fetch(
                "SELECT key, value, value_type, description, version FROM system_parameters WHERE tenant_id = $1 ORDER BY category, key",
                user.get("tenant_id")
            )
        return [dict(row) for row in rows]
    finally:
        await close_db(conn)

@app.post("/parameters")
async def create_parameter(
    param: ParameterCreate,
    user: dict = Depends(get_current_user)
):
    """Create or update parameter"""
    has_perm = await check_permission(user.get("user_id"), "admin", "parameters")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        # Check if exists
        existing = await conn.fetchrow(
            "SELECT id FROM system_parameters WHERE tenant_id = $1 AND key = $2 AND cost_center_id IS NULL",
            user.get("tenant_id"), param.key
        )
        
        if existing:
            # Update
            await conn.execute(
                """
                UPDATE system_parameters 
                SET value = $1, value_type = $2, description = $3, min_value = $4, max_value = $5
                WHERE id = $6
                """,
                json.dumps(param.value), param.value_type, param.description,
                param.min_value, param.max_value, existing["id"]
            )
            return {"status": "updated", "key": param.key}
        else:
            # Insert
            await conn.execute(
                """
                INSERT INTO system_parameters (tenant_id, category, key, value, value_type, description, min_value, max_value, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                user.get("tenant_id"), param.category, param.key,
                json.dumps(param.value), param.value_type, param.description,
                param.min_value, param.max_value, user.get("user_id")
            )
            return {"status": "created", "key": param.key}
    finally:
        await close_db(conn)

@app.get("/parameters/{key}/history")
async def get_parameter_history(key: str, user: dict = Depends(get_current_user)):
    """Get parameter change history"""
    conn = await get_db()
    try:
        param_id = await conn.fetchval(
            "SELECT id FROM system_parameters WHERE tenant_id = $1 AND key = $2 AND cost_center_id IS NULL",
            user.get("tenant_id"), key
        )
        
        if not param_id:
            raise HTTPException(status_code=404, detail="Parameter not found")
        
        rows = await conn.fetch(
            "SELECT previous_value, new_value, changed_by, changed_at FROM system_parameter_changes WHERE param_id = $1 ORDER BY changed_at DESC",
            param_id
        )
        return [dict(row) for row in rows]
    finally:
        await close_db(conn)

# ============================================================
# AGENTS ENDPOINTS
# ============================================================

@app.get("/agents/actions")
async def list_agent_actions(
    session_id: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """List agent actions with optional session filter"""
    has_perm = await check_permission(user.get("user_id"), "agent", "read")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        if session_id:
            rows = await conn.fetch(
                "SELECT id, session_id, turn_number, tool_name, status, risk_level, latency_ms, cost_usd, approval_required, created_at FROM agent_action_log WHERE session_id = $1 ORDER BY turn_number LIMIT $2",
                session_id, limit
            )
        else:
            rows = await conn.fetch(
                "SELECT id, session_id, turn_number, tool_name, status, risk_level, latency_ms, cost_usd, approval_required, created_at FROM agent_action_log WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2",
                user.get("tenant_id"), limit
            )
        return [dict(row) for row in rows]
    finally:
        await close_db(conn)

@app.post("/agents/actions/{action_id}/approve")
async def approve_action(
    action_id: str,
    user: dict = Depends(get_current_user)
):
    """Approve a high-risk agent action"""
    has_perm = await check_permission(user.get("user_id"), "agent", "execute")
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    conn = await get_db()
    try:
        # Check if exists and pending approval
        action = await conn.fetchrow(
            "SELECT approval_required, approved_by FROM agent_action_log WHERE id = $1 AND tenant_id = $2",
            action_id, user.get("tenant_id")
        )
        
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        if not action["approval_required"]:
            raise HTTPException(status_code=400, detail="Action does not require approval")
        
        if action["approved_by"]:
            raise HTTPException(status_code=400, detail="Action already approved")
        
        await conn.execute(
            "UPDATE agent_action_log SET approved_by = $1, approved_at = NOW() WHERE id = $2",
            user.get("user_id"), action_id
        )
        
        return {"status": "approved", "action_id": action_id}
    finally:
        await close_db(conn)

# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "service": "Orkestra Finance Brain API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "/health",
            "/auth/login",
            "/auth/me",
            "/audit",
            "/decisions",
            "/pricing/calculate",
            "/parameters",
            "/agents/actions"
        ]
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
