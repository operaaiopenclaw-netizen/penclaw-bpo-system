# dashboard.py - Orkestra Simple Dashboard
# Servidor de dashboard web simples

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
from datetime import datetime


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎛️ Orkestra Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: #888;
            font-size: 1.1em;
        }
        
        /* Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 40px rgba(0,212,255,0.1);
        }
        .card-icon {
            font-size: 2.5em;
            margin-bottom: 15px;
        }
        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .card-label {
            color: #888;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card-trend {
            margin-top: 10px;
            font-size: 0.9em;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-block;
        }
        .trend-up { background: rgba(0,255,0,0.2); color: #0f0; }
        .trend-down { background: rgba(255,0,0,0.2); color: #f00; }
        .trend-stable { background: rgba(255,255,0,0.2); color: #ff0; }
        
        /* Insights */
        .section {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .insight-item {
            background: rgba(255,255,255,0.03);
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .insight-positive { border-color: #0f0; }
        .insight-warning { border-color: #ff0; }
        .insight-negative { border-color: #f00; }
        .insight-icon {
            font-size: 1.5em;
        }
        .insight-text {
            flex: 1;
        }
        .insight-meta {
            color: #888;
            font-size: 0.85em;
        }
        
        /* Rules */
        .rule-item {
            background: rgba(255,255,255,0.03);
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 4px solid;
        }
        .rule-critical { border-color: #f00; }
        .rule-high { border-color: #ff6b6b; }
        .rule-medium { border-color: #ffd93d; }
        .rule-low { border-color: #6bcf7f; }
        .rule-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .rule-priority {
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
        }
        .priority-critical { background: #f00; }
        .priority-high { background: #ff6b6b; }
        .priority-medium { background: #ffd93d; color: #000; }
        .priority-low { background: #6bcf7f; }
        .rule-action {
            color: #ddd;
            font-size: 0.95em;
        }
        .rule-rationale {
            color: #888;
            font-size: 0.85em;
            margin-top: 5px;
        }
        
        /* Events Table */
        .events-table {
            width: 100%;
            border-collapse: collapse;
        }
        .events-table th,
        .events-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .events-table th {
            color: #888;
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 1px;
        }
        .badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
        }
        .badge-approve { background: rgba(0,255,0,0.2); color: #0f0; }
        .badge-review { background: rgba(255,255,0,0.2); color: #ff0; }
        .badge-reject { background: rgba(255,0,0,0.2); color: #f00; }
        
        .refresh-btn {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 12px 25px;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border: none;
            border-radius: 30px;
            color: #fff;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 30px rgba(0,212,255,0.3);
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎛️ ORKESTRA</h1>
            <p class="subtitle">Dashboard de Gestão de Eventos</p>
            <p style="color:#666; margin-top:10px;">Última atualização: {{last_update}}</p>
            <br>
            <a href="/refresh" class="refresh-btn">🔄 Atualizar Dados</a>
        </header>
        
        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-value">{{total_revenue}}</div>
                <div class="card-label">Receita Total</div>
            </div>
            <div class="card">
                <div class="card-icon">📉</div>
                <div class="card-value">{{total_cost}}</div>
                <div class="card-label">Custo Total</div>
            </div>
            <div class="card">
                <div class="card-icon">📊</div>
                <div class="card-value">{{avg_margin}}%</div>
                <div class="card-label">Margem Média</div>
                <div class="card-trend {{trend_class}}">{{trend_text}}</div>
            </div>
            <div class="card">
                <div class="card-icon">🎯</div>
                <div class="card-value">{{events_count}}</div>
                <div class="card-label">Eventos</div>
            </div>
        </div>
        
        <!-- Insights Section -->
        <div class="section">
            <h2 class="section-title">📊 Insights do Learning Engine</h2>
            {{insights_html}}
        </div>
        
        <!-- Rules Section -->
        <div class="section">
            <h2 class="section-title">⚙️ Regras Sugeridas</h2>
            {{rules_html}}
        </div>
        
        <!-- Events Table -->
        <div class="section">
            <h2 class="section-title">🎯 Eventos Analisados</h2>
            <table class="events-table">
                <thead>
                    <tr>
                        <th>Evento</th>
                        <th>Receita</th>
                        <th>Custo</th>
                        <th>Margem</th>
                        <th>Decisão</th>
                    </tr>
                </thead>
                <tbody>
                    {{events_rows}}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Orkestra Finance Brain v1.0 | Auto-gerado em {{timestamp}}</p>
        </div>
    </div>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler para servidor de dashboard."""
    
    def log_message(self, format, *args):
        """Silenciar logs."""
        pass
    
    def do_GET(self):
        """Processa requisições GET."""
        path = self.path
        
        if path == "/" or path == "/dashboard":
            self.send_dashboard()
        elif path == "/api/status":
            self.send_json(self.get_status())
        elif path == "/api/insights":
            self.send_json(self.get_insights())
        elif path == "/refresh":
            self.redirect("/")
        else:
            self.send_error(404)
    
    def send_dashboard(self):
        """Renderiza e envia o dashboard."""
        html = self.generate_dashboard()
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_json(self, data):
        """Envia resposta JSON."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def redirect(self, url):
        """Redireciona para URL."""
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()
    
    def generate_dashboard(self) -> str:
        """Gera HTML do dashboard com dados reais."""
        # Carregar dados
        status = self.get_status()
        insights = self.get_insights()
        
        # Calcular estatísticas
        total_revenue = status.get("total_revenue", 0)
        total_cost = status.get("total_cost", 0)
        avg_margin = status.get("avg_margin", 0)
        events_count = status.get("events_count", 0)
        
        # Insights HTML
        insights_list = insights.get("insights", [])
        insights_html = ""
        
        if insights_list:
            for i in insights_list[:5]:
                tipo = i.get("type", "neutro")
                rec = i.get("recommendation", "")
                
                css_class = "insight-positive" if "✅" in rec or "positivo" in tipo else \
                           "insight-warning" if "⚠️" in rec or "neutro" in tipo else "insight-negative"
                icon = "✅" if css_class == "insight-positive" else "⚠️" if css_class == "insight-warning" else "🔴"
                
                insights_html += f"""
                <div class="insight-item {css_class}">
                    <span class="insight-icon">{icon}</span>
                    <span class="insight-text">{rec}</span>
                </div>
                """
        else:
            insights_html = "<p style='color:#666;'>Nenhum insight disponível. Execute o Learning Engine.</p>"
        
        # Rules HTML
        rules_list = insights.get("rules", [])
        rules_html = ""
        
        if rules_list:
            for r in rules_list[:5]:
                priority = r.get("priority", "LOW").lower()
                action = r.get("action", "")
                rationale = r.get("rationale", "")
                
                rules_html += f"""
                <div class="rule-item rule-{priority}">
                    <div class="rule-header">
                        <span class="rule-priority priority-{priority}">{priority.upper()}</span>
                    </div>
                    <div class="rule-action">{action}</div>
                    <div class="rule-rationale">{rationale}</div>
                </div>
                """
        else:
            rules_html = "<p style='color:#666;'>Nenhuma regra gerada.</p>"
        
        # Events rows
        events = status.get("events", [])
        events_rows = ""
        
        for e in events[:10]:
            decision = e.get("decision", "UNKNOWN")
            badge_class = f"badge-{decision.lower()}"
            margin = e.get("margin", 0)
            
            events_rows += f"""
            <tr>
                <td>{e.get('name', 'N/A')}</td>
                <td>R$ {e.get('revenue', 0):,.0f}</td>
                <td>R$ {e.get('cost', 0):,.0f}</td>
                <td>{margin*100:.1f}%</td>
                <td><span class="badge {badge_class}">{decision}</span></td>
            </tr>
            """
        
        if not events_rows:
            events_rows = "<tr><td colspan='5' style='text-align:center;color:#666;'>Nenhum evento analisado</td></tr>"
        
        # Tendência
        trend = status.get("trend", "stable")
        trend_class = "trend-up" if trend == "improving" else "trend-down" if trend == "declining" else "trend-stable"
        trend_text = "↑ Melhorando" if trend == "improving" else "↓ Piorando" if trend == "declining" else "→ Estável"
        
        # Substituir placeholders
        html = DASHBOARD_HTML
        html = html.replace("{{last_update}}", datetime.now().strftime("%d/%m/%Y %H:%M"))
        html = html.replace("{{total_revenue}}", f"R$ {total_revenue:,.0f}")
        html = html.replace("{{total_cost}}", f"R$ {total_cost:,.0f}")
        html = html.replace("{{avg_margin}}", f"{avg_margin*100:.1f}")
        html = html.replace("{{events_count}}", str(events_count))
        html = html.replace("{{trend_class}}", trend_class)
        html = html.replace("{{trend_text}}", trend_text)
        html = html.replace("{{insights_html}}", insights_html)
        html = html.replace("{{rules_html}}", rules_html)
        html = html.replace("{{events_rows}}", events_rows)
        html = html.replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        return html
    
    def get_status(self) -> dict:
        """Retorna status do sistema."""
        try:
            # Carregar pipeline report
            report_path = Path("orkestra/memory/pipeline_report.json")
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                summary = report.get("summary", {})
                events = report.get("events", [])
                
                return {
                    "total_revenue": summary.get("total_revenue", 0),
                    "total_cost": summary.get("total_cost", 0),
                    "avg_margin": summary.get("avg_margin", 0),
                    "events_count": summary.get("events_analyzed", 0),
                    "events": events,
                    "trend": "stable"
                }
        except:
            pass
        
        return {
            "total_revenue": 0,
            "total_cost": 0,
            "avg_margin": 0,
            "events_count": 0,
            "events": [],
            "trend": "stable"
        }
    
    def get_insights(self) -> dict:
        """Retorna insights do learning engine."""
        try:
            report_path = Path("orkestra/memory/learning_report.json")
            if report_path.exists():
                with open(report_path) as f:
                    report = json.load(f)
                
                return {
                    "insights": report.get("insights", []),
                    "rules": report.get("rules", [])
                }
        except:
            pass
        
        return {"insights": [], "rules": []}


def run_dashboard(port: int = 8080):
    """Inicia servidor de dashboard."""
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"\n🎛️  ORKESTRA DASHBOARD")
    print(f"=" * 60)
    print(f"Servidor iniciado em: http://localhost:{port}")
    print(f"Dashboard: http://localhost:{port}/dashboard")
    print(f"API Status: http://localhost:{port}/api/status")
    print(f"Pressione Ctrl+C para parar")
    print(f"=" * 60 + "\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor encerrado")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", "-p", type=int, default=8080)
    args = parser.parse_args()
    
    run_dashboard(args.port)
