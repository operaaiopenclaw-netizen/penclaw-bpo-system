#!/usr/bin/env python3
"""
EXECUTIVE REPORT ENGINE
Relatório executivo com storytelling de dados operacionais

REGRAS:
- NÃO usar jargão técnico
- Apresentar "o que aconteceu" e "por que importa"
- Linguagem de negócio
- Cada insight com contexto
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, asdict
from statistics import mean, median

DATA_DIR = Path(__file__).parent / "kitchen_data"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class ExecutiveInsight:
    category: str  # "financial", "operational", "strategic"
    headline: str  # Headline impactante
    what_happened: str  # O que aconteceu (fato)
    why_it_matters: str  # Por que importa (contexto)
    numbers: Dict[str, Any]  # Números relevantes
    recommendation: str  # Recomendação executiva
    priority: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    timestamp: str


class ExecutiveReportEngine:
    """Motor de geração de relatório executivo"""
    
    def __init__(self):
        self.data_cache = {}
        self.insights = []
        self.stories = []
    
    def load_json(self, filename: str) -> Dict:
        """Carrega JSON com cache"""
        if filename in self.data_cache:
            return self.data_cache[filename]
        
        filepath = DATA_DIR / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.data_cache[filename] = data
                return data
        return {}
    
    def load_all_data(self):
        """Carrega todos os dados dos engines"""
        print("   📥 Carregando dados de todos os engines...")
        
        self.financial_audit = self.load_json("financial_audit.json")
        self.item_performance = self.load_json("item_performance.json")
        self.menu_strategy = self.load_json("menu_strategy.json")
        self.dre_summary = self.load_json("dre_summary.json")
        self.pricing_suggestions = self.load_json("pricing_suggestions.json")
        self.calibration_suggestions = self.load_json("calibration_suggestions.json")
        self.decisions = self.load_json("decisions.json")
        self.waste_log = self.load_json("waste_log.json")
        self.fixed_allocations = self.load_json("fixed_allocations.json")
        
        print(f"   ✓ {len(self.data_cache)} arquivos carregados")
    
    def analyze_financial_story(self):
        """
        1. HISTÓRIA FINANCEIRA
        Extrai insights de saúde financeira dos eventos
        """
        audits = self.financial_audit.get("audits", [])
        
        if not audits:
            self._add_no_data_insight("financial")
            return
        
        # Separar por status
        inconsistent = [a for a in audits if a.get("status") == "INCONSISTENTE"]
        alertas = [a for a in audits if a.get("status") == "ALERTA"]
        consistentes = [a for a in audits if a.get("status") == "CONSISTENTE"]
        
        # Eventos em risco
        em_risco = [a for a in audits if a.get("risco_financeiro") == "ALTO"]
        
        # História 1: Risco Financeiro
        if em_risco:
            total_receita = sum(a.get("receita_total", 0) or 0 for a in em_risco)
            
            self.insights.append(ExecutiveInsight(
                category="financial",
                headline=f"🚨 {len(em_risco)} eventos em risco financeiro crítico",
                what_happened=f"Identificamos {len(em_risco)} eventos onde os dados financeiros apresentam inconsistências graves ou margens críticas. Estes eventos representam R$ {total_receita:,.2f} em receita.",
                why_it_matters="Eventos com inconsistências financeiras podem estar gerando prejuízos não detectados. A falta de confiança nos números impede decisões estratégicas. Cada evento em risco precisa de revisão imediata antes do próximo job.",
                numbers={
                    "eventos_risco": len(em_risco),
                    "receita_em_risco": total_receita,
                    "percentual_total": (len(em_risco) / len(audits) * 100) if audits else 0
                },
                recommendation="Urgente: Pausar novos agendamentos até resolver inconsistências. Reauditar eventos de alto risco individualmente.",
                priority="CRITICAL" if len(em_risco) > 3 else "HIGH",
                timestamp=datetime.now().isoformat()
            ))
        
        # História 2: Margens Saudáveis
        margens_baixas = [a for a in audits if a.get("margem_bruta_pct") and a["margem_bruta_pct"] < 20]
        margens_boas = [a for a in audits if a.get("margem_bruta_pct") and a["margem_bruta_pct"] >= 30]
        
        if margens_baixas:
            self.insights.append(ExecutiveInsight(
                category="financial",
                headline=f"⚠️ {len(margens_baixas)} eventos com margem abaixo da meta",
                what_happened=f"{len(margens_baixas)} eventos operaram com margem bruta inferior a 20%. O ideal é 30%+. A média de margem destes eventos foi de {mean(a['margem_bruta_pct'] for a in margens_baixas):.1f}%.",
                why_it_matters="Margens abaixo de 20% deixam pouca margem para imprevistos. Após alocar custos fixos, o lucro líquido pode ser quase zero ou negativo. O negócio vinga de volume, não de margem.",
                numbers={
                    "eventos_baixa_margem": len(margens_baixas),
                    "margem_media_baixa": round(mean(a['margem_bruta_pct'] for a in margens_baixas), 1),
                    "eventos_meta": len(margens_boas)
                },
                recommendation="Revisar orçamento para eventos similares. Considerar aumento de preço ou redução de custo em 10-15%.",
                priority="HIGH",
                timestamp=datetime.now().isoformat()
            ))
        
        # História 3: Performance Financeira
        if audits:
            margens = [a.get("margem_bruta_pct") for a in audits if a.get("margem_bruta_pct")]
            if margens:
                margem_media = mean(margens)
                margem_mediana = median(margens)
                
                self.insights.append(ExecutiveInsight(
                    category="financial",
                    headline=f"📊 Operando com margem média de {margem_media:.1f}%",
                    what_happened=f"A carteira de eventos analisada apresenta margem média de {margem_media:.1f}%, com mediana de {margem_mediana:.1f}%. {len(consistentes)} de {len(audits)} eventos têm dados consistentes e auditáveis.",
                    why_it_matters=f"A margem mediana ({margem_mediana:.1f}%) mostra que metade dos eventos performa {'acima' if margem_mediana > 25 else 'abaixo'} do esperado. A diferença entre média e mediana indica {'concentração' if margem_mediana > margem_media else 'presença'} de outliers. A taxa de {len(consistentes)/len(audits)*100:.0f}% de consistência de dados é {'excelente' if len(consistentes)/len(audits) > 0.8 else 'precisa de melhoria'} para tomada de decisão.",
                    numbers={
                        "margem_media": round(margem_media, 1),
                        "margem_mediana": round(margem_mediana, 1),
                        "eventos_totais": len(audits),
                        "eventos_auditaveis": len(consistentes)
                    },
                    recommendation="Manter controle rigoroso de margem em eventos abaixo da média. Focar em replicar modelos dos eventos acima da mediana.",
                    priority="MEDIUM",
                    timestamp=datetime.now().isoformat()
                ))
    
    def analyze_operational_story(self):
        """
        2. HISTÓRIA OPERACIONAL
        Extrai insights de produção, desperdício e eficiência
        """
        performances = self.item_performance.get("performances", [])
        waste_data = self.waste_log.get("registros", {})
        
        if not performances:
            self._add_no_data_insight("operational")
            return
        
        # História: Desperdício
        waste_pcts = [p.get("waste_pct") for p in performances if p.get("waste_pct")]
        if waste_pcts:
            avg_waste = mean(waste_pcts)
            waste_criticos = [p for p in performances if p.get("waste_pct") and p["waste_pct"] > 15]
            
            if waste_criticos:
                self.insights.append(ExecutiveInsight(
                    category="operational",
                    headline=f"🗑️ {len(waste_criticos)} itens com desperdício superior a 15%",
                    what_happened=f"Detectamos {len(waste_criticos)} itens que consistentemente apresentam desperdício acima de 15%. A média de desperdício nestes itens é de {mean(p['waste_pct'] for p in waste_criticos):.1f}%. Estima-se perda de matéria-prima em cada evento.",
                    why_it_matters="Desperdício acima de 15% significa que para cada 100 pratos produzidos, 15+ são descartados. Além do custo direto, há custo oculto de mão-de-obra, energia e espaço. Este padrão sugere overprodução crônica ou erros na ficha técnica.",
                    numbers={
                        "itens_criticos": len(waste_criticos),
                        "desperdicio_medio_critico": round(mean(p['waste_pct'] for p in waste_criticos), 1),
                        "desperdicio_geral": round(avg_waste, 1)
                    },
                    recommendation="Revisar imediatamente a ficha técnica destes itens. Reduzir produção em 15-20% para testar se atende demanda real.",
                    priority="HIGH",
                    timestamp=datetime.now().isoformat()
                ))
        
        # História: Mais vendidos
        if performances:
            by_volume = sorted([p for p in performances if p.get("quantity_sold")], 
                             key=lambda x: x["quantity_sold"], reverse=True)[:5]
            
            if by_volume:
                total_vendas = sum(p["quantity_sold"] for p in by_volume)
                top_item = by_volume[0]
                
                self.insights.append(ExecutiveInsight(
                    category="operational",
                    headline=f"🥇 {top_item['recipe_name']} é o carro-chefe com {top_item['quantity_sold']:.0f} vendas",
                    what_happened=f"O item mais vendido foi '{top_item['recipe_name']}' com {top_item['quantity_sold']:.0f} unidades. Os 5 itens mais vendidos somam {total_vendas:.0f} unidades. {'A margem deste item está boa' if top_item.get('margin_pct') and top_item['margin_pct'] > 25 else 'ATENÇÃO: este item tem margem baixa de ' + str(round(top_item.get('margin_pct', 0), 1)) + '%'}.",
                    why_it_matters="Carros-chefes definem a reputação do evento. Se o item mais vendido tem margem baixa, o evento inteiro sofre. Se tem margem alta, fortalece toda a operação. A popularidade deste item pode ser usada para vender bundles mais lucrativos.",
                    numbers={
                        "top_item": top_item['recipe_name'],
                        "vendas_top": top_item['quantity_sold'],
                        "margem_top": round(top_item.get('margin_pct', 0), 1),
                        "total_top5": total_vendas
                    },
                    recommendation="Destacar os top 5 itens no cardápio. Se margem do top item for <25%, criar versão 'premium' mais lucrativa.",
                    priority="MEDIUM" if top_item.get('margin_pct', 0) > 25 else "HIGH",
                    timestamp=datetime.now().isoformat()
                ))
    
    def analyze_strategic_story(self):
        """
        3. HISTÓRIA ESTRATÉGICA
        Extrai insights do cardápio e estratégia
        """
        strategy = self.menu_strategy.get("strategies", [])
        
        if not strategy:
            self._add_no_data_insight("strategic")
            return
        
        # Análise da Matriz BCG
        estrelas = [s for s in strategy if s.get("classification") == "ESTRELA"]
        vacas = [s for s in strategy if s.get("classification") == "VACA_LEITEIRA"]
        armadilhas = [s for s in strategy if s.get("classification") == "ARMADILHA"]
        problemas = [s for s in strategy if s.get("classification") == "PROBLEMA"]
        
        # História: Armadilhas (atenção máxima)
        if armadilhas:
            receita_armadilha = sum(s.get("total_revenue", 0) or 0 for s in armadilhas)
            
            self.insights.append(ExecutiveInsight(
                category="strategic",
                headline=f"🚨 {len(armadilhas)} 'ARMADILHAS' queimando margem do negócio",
                what_happened=f"Identificamos {len(armadilhas)} itens que vendem bem mas têm margem baixa (<50%). Estes são as 'armadilhas' do cardápio. Apesar de populares, cada venda reduz a rentabilidade geral. Representam R$ {receita_armadilha:,.2f} em receita com margem crítica.",
                why_it_matters="Armadilhas são perigosas porque a alta venda mascara a baixa lucratividade. O time produz muito, trabalha duro, mas o resultado é ruim. Clientes amam, mas o negócio sangra. São os itens que 'matam' a margem do evento sorrateiramente.",
                numbers={
                    "armadilhas": len(armadilhas),
                    "receita_em_risco": receita_armadilha,
                    "percentual_cardapio": (len(armadilhas) / len(strategy) * 100) if strategy else 0
                },
                recommendation="URGENTE: Aumentar preço em 10-15% ou reduzir custo. Se resposta do mercado for negativa, substituir por alternativa própria mais lucrativa.",
                priority="CRITICAL" if len(armadilhas) > 2 else "HIGH",
                timestamp=datetime.now().isoformat()
            ))
        
        # História: Estrelas (potencial)
        if estrelas:
            self.insights.append(ExecutiveInsight(
                category="strategic",
                headline=f"⭐ {len(estrelas)} 'ESTRELAS' sustentando resultados",
                what_happened=f"Temos {len(estrelas)} itens de alta performance - vendem bem (>30 unidades) com margem excelente (>60%). Estes são os verdadeiros ganha-pão. Eles compensam as perdas de outros itens.",
                why_it_matters="Estrelas são o ouro do cardápio. Devem ser protegidas, promovidas e colocadas em destaque. A receita e margem destes itens definem o sucesso financeiro do evento. Problemas em estrelas impactam desproporcionalmente o resultado.",
                numbers={
                    "estrelas": len(estrelas),
                    "receita_estrelas": sum(s.get("total_revenue", 0) or 0 for s in estrelas),
                    "margem_media": round(mean(s.get("avg_margin_pct", 0) for s in estrelas), 1) if estrelas else 0
                },
                recommendation="Criar pacotes especiais destacando estrelas. Usar como âncora em propostas. Nunca comprometer qualidade destes itens.",
                priority="MEDIUM",
                timestamp=datetime.now().isoformat()
            ))
        
        # História: Vacas Leiteiras (oportunidade)
        if vacas:
            self.insights.append(ExecutiveInsight(
                category="strategic",
                headline=f"🐮 {len(vacas)} itens com potencial de crescimento não explorado",
                what_happened=f"{len(vacas)} itens têm margem boa (>50%) mas vendem abaixo do potencial. São 'vacas leiteiras' - quando bem alimentadas (marketing), podem produzir mais sem aumentar custo.",
                why_it_matters="Estes itens provam que o negócio pode ser lucrativo, mas estamos deixando dinheiro na mesa. Baixa venda + alta margem = demanda não atendida. Pequeno investimento em divulgação pode multiplicar receita sem aumentar custo operacional.",
                numbers={
                    "vacas": len(vacas),
                    "margem_media": round(mean(s.get("avg_margin_pct", 0) for s in vacas), 1) if vacas else 0,
                    "vendas_medias": round(mean(s.get("total_quantity_sold", 0) for s in vacas), 0) if vacas else 0
                },
                recommendation="Testar fotos profissionais e posição premium no cardápio. Oferecer em degustação. Criar bundle 'chef's choice'.",
                priority="HIGH",
                timestamp=datetime.now().isoformat()
            ))
        
        # História: Problemas (corte)
        if problemas:
            self.insights.append(ExecutiveInsight(
                category="strategic",
                headline=f"❌ {len(problemas)} itens candidatos a remoção do cardápio",
                what_happened=f"{len(problemas)} itens apresentam baixa venda + baixa margem. Consomem tempo de equipe, espaço de armazenamento e atenção gerencial sem retorno proporcional.",
                why_it_matters="Itens problemáticos custam mais do que seu preço. Há custo oculto de complexidade no cardápio, treinamento da equipe, gestão de estoque e atenção desviada de itens importantes. Menos pode ser mais.",
                numbers={
                    "problemas": len(problemas),
                    "percentual": (len(problemas) / len(strategy) * 100) if strategy else 0
                },
                recommendation="Reformular radicalmente ou substituir por alternativa já testada. Não manter 'por dó'.",
                priority="MEDIUM",
                timestamp=datetime.now().isoformat()
            ))
    
    def generate_executive_stories(self):
        """Gera narrativas executivas completas"""
        
        # História principal: Onde o negócio está
        critical = [i for i in self.insights if i.priority == "CRITICAL"]
        high = [i for i in self.insights if i.priority == "HIGH"]
        
        if critical:
            status = "🚨 SITUAÇÃO CRÍTICA"
            summary = f"Identificamos {len(critical)} problemas críticos que exigem atenção imediata. "
            summary += "O negócio está operando com riscos financeiros significativos. "
        elif high:
            status = "⚠️ ATENÇÃO NECESSÁRIA"
            summary = f"Detectamos {len(high)} áreas de preocupação que impactam resultados. "
            summary += "Ajustes são recomendados nas próximas semanas. "
        else:
            status = "✅ OPERACIONALMENTE SAUDÁVEL"
            summary = "Os indicadores mostram operação dentro dos parâmetros aceitáveis. "
            summary += "Foco deve ser em otimização e crescimento. "
        
        # Top 3 prioridades
        top_insights = sorted(self.insights, 
                            key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.priority, 4))[:3]
        
        self.stories.append({
            "story_type": "executive_summary",
            "status": status,
            "summary": summary,
            "top_priorities": [
                {
                    "headline": i.headline,
                    "why_it_matters": i.why_it_matters,
                    "action": i.recommendation
                }
                for i in top_insights
            ],
            "total_insights": len(self.insights),
            "by_category": {
                "financial": len([i for i in self.insights if i.category == "financial"]),
                "operational": len([i for i in self.insights if i.category == "operational"]),
                "strategic": len([i for i in self.insights if i.category == "strategic"])
            },
            "timestamp": datetime.now().isoformat()
        })
    
    def _add_no_data_insight(self, category: str):
        """Adiciona insight quando não há dados"""
        messages = {
            "financial": "Dados financeiros insuficientes para análise completa. Execute financial_truth_audit.py.",
            "operational": "Dados operacionais limitados. Execute production_execution e waste_log.",
            "strategic": "Estratégia não definida. Execute menu_optimization_engine.py para matriz BCG."
        }
        
        self.insights.append(ExecutiveInsight(
            category=category,
            headline=f"ℹ️ Dados de {category} insuficientes para storytelling completo",
            what_happened=messages.get(category, "Dados insuficientes"),
            why_it_matters="Sem dados históricos, o sistema não consegue identificar padrões. Recomendações ficam genéricas.",
            numbers={},
            recommendation="Popular bases de dados com histórico de eventos antes da próxima análise.",
            priority="LOW",
            timestamp=datetime.now().isoformat()
        ))
    
    def save_report(self):
        """Salva relatório executivo"""
        
        output = {
            "_meta": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "format": "executive storytelling",
                "language": "business",
                "disclaimer": "Relatório gerado automaticamente. Decisões estratégicas requerem validação humana.",
                "total_insights": len(self.insights),
                "stories_generated": len(self.stories)
            },
            "executive_summary": self.stories[0] if self.stories else {},
            "insights": [asdict(i) for i in self.insights],
            "stories": self.stories
        }
        
        # Salvar JSON
        filepath = DATA_DIR / "executive_report.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Relatório salvo em: kitchen_data/executive_report.json")
    
    def print_executive_report(self):
        """Imprime relatório executivo formatado"""
        
        print("\n" + "="*90)
        print("📊 EXECUTIVE REPORT - RELATÓRIO PARA DECISÃO")
        print("="*90)
        print("   Linguagem de negócio | Sem jargão técnico | Insights acionáveis")
        print("="*90)
        
        # Status geral
        if self.stories:
            story = self.stories[0]
            print(f"\n{story['status']}")
            print(f"{'─'*90}")
            print(f"   {story['summary']}")
            print(f"\n   TOTAL DE INSIGHTS: {story['total_insights']}")
            print(f"   • Financeiros: {story['by_category'].get('financial', 0)}")
            print(f"   • Operacionais: {story['by_category'].get('operational', 0)}")
            print(f"   • Estratégicos: {story['by_category'].get('strategic', 0)}")
        
        # Insights por categoria
        categories = ["financial", "operational", "strategic"]
        cat_names = {
            "financial": "💰 HISTÓRIA FINANCEIRA",
            "operational": "⚙️ HISTÓRIA OPERACIONAL",
            "strategic": "🎯 HISTÓRIA ESTRATÉGICA"
        }
        
        for cat in categories:
            cat_insights = [i for i in self.insights if i.category == cat]
            if cat_insights:
                print(f"\n{'='*90}")
                print(f"{cat_names.get(cat, cat)}")
                print(f"{'='*90}")
                
                # Ordenar por prioridade
                priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
                cat_insights.sort(key=lambda x: priority_order.get(x.priority, 4))
                
                for i, insight in enumerate(cat_insights, 1):
                    emoji_priority = {
                        "CRITICAL": "🚨",
                        "HIGH": "🔴",
                        "MEDIUM": "🟡",
                        "LOW": "🟢"
                    }
                    
                    print(f"\n   {emoji_priority.get(insight.priority, '❓')} {insight.headline}")
                    print(f"   {'─'*80}")
                    print(f"   📌 O QUE ACONTECEU:")
                    print(f"      {insight.what_happened}")
                    print(f"\n   💡 POR QUE IMPORTA:")
                    print(f"      {insight.why_it_matters}")
                    
                    if insight.numbers:
                        print(f"\n   📊 NÚMEROS:")
                        for key, value in insight.numbers.items():
                            if isinstance(value, float):
                                print(f"      • {key}: {value:.2f}")
                            else:
                                print(f"      • {key}: {value}")
                    
                    print(f"\n   ✅ RECOMENDAÇÃO:")
                    print(f"      {insight.recommendation}")
                    print(f"{'─'*80}")
        
        # Rodapé
        print(f"\n{'='*90}")
        print("⚠️  NOTA DO SISTEMA")
        print(f"{'='*90}")
        print("   Este relatório foi gerado automaticamente com base em dados operacionais.")
        print("   Cada insight inclui contexto para facilitar decisões estratégicas.")
        print("   Decisões finais requerem validação humana e consideração de fatores externos.")
        print(f"{'='*90}\n")


def main():
    """Função principal"""
    
    print("🎛️ EXECUTIVE REPORT ENGINE - Orkestra Finance Brain")
    print("="*90)
    print("\n📊 Gerando storytelling executivo a partir de dados operacionais")
    print("   Modo: linguagem de negócio | Sem jargão técnico | Insights acionáveis")
    
    engine = ExecutiveReportEngine()
    
    # Carregar dados
    engine.load_all_data()
    
    # Analisar e gerar histórias
    print("\n🔍 Analisando padrões...")
    
    print("   📈 Extraindo história financeira...")
    engine.analyze_financial_story()
    
    print("   ⚙️ Extraindo história operacional...")
    engine.analyze_operational_story()
    
    print("   🎯 Extraindo história estratégica...")
    engine.analyze_strategic_story()
    
    print("   📋 Gerando narrativas executivas...")
    engine.generate_executive_stories()
    
    if not engine.insights:
        print("\n⚠️  Dados insuficientes para gerar insights executivos")
        print("   Execute os engines anteriores primeiro:")
        print("   - financial_truth_audit.py")
        print("   - item_intelligence_engine.py")
        print("   - menu_optimization_engine.py")
        return
    
    # Gerar saídas
    engine.save_report()
    engine.print_executive_report()
    
    print(f"\n✅ Executive Report Engine completado!")
    print(f"   {len(engine.insights)} insights gerados")
    print(f"   {len(engine.stories)} histórias executivas")


if __name__ == "__main__":
    main()
