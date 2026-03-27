# real_data_ingestion.py - Orkestra Real Data Ingestion Engine
# Transforma PDFs e planilhas reais em datasets estruturados

import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FinancialRecord:
    """Registro financeiro normalizado."""
    company: str  # OPERA/STATUS ou LA ORANA
    month: str    # 01-12
    year: str     # 2024 ou 2025
    revenue_operational: float
    revenue_events: float
    tax: float
    cmv: float
    other_costs: float
    payroll: float
    admin: float
    variable: float
    financial: float
    gross_result: float
    intercompany_receivable: float
    intercompany_payable: float
    partner_distributions: float
    net_result: float
    source_file: str
    inconsistencies: List[str]


class RealDataIngestionEngine:
    """
    Motor de ingestão de dados reais.
    Transforma fontes brutas em datasets estruturados.
    """
    
    COMPANIES = ["OPERA"]

    def __init__(self):
        self.records: List[FinancialRecord] = []
        self.intercompany_transactions: List[Dict] = []
        self.partner_withdrawals: List[Dict] = []
        self.inconsistencies: List[Dict] = []
        
    def parse_pdf_text(self, text: str, company: str, source_file: str) -> List[FinancialRecord]:
        """
        Parse de texto extraído de PDF.
        Extrai linhas de DRE e normaliza.
        """
        records = []
        
        # Detectar período (mês/ano)
        period_match = re.search(r'(Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro|JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)\s+(\d{4})', text, re.IGNORECASE)
        
        if period_match:
            month_name = period_match.group(1).upper()
            year = period_match.group(2)
            month_map = {
                'JANEIRO': '01', 'JAN': '01',
                'FEVEREIRO': '02', 'FEV': '02',
                'MARÇO': '03', 'MAR': '03',
                'ABRIL': '04', 'ABR': '04',
                'MAIO': '05', 'MAI': '05',
                'JUNHO': '06', 'JUN': '06',
                'JULHO': '07', 'JUL': '07',
                'AGOSTO': '08', 'AGO': '08',
                'SETEMBRO': '09', 'SET': '09',
                'OUTUBRO': '10', 'OUT': '10',
                'NOVEMBRO': '11', 'NOV': '11',
                'DEZEMBRO': '12', 'DEZ': '12'
            }
            month = month_map.get(month_name, '01')
        else:
            month, year = "01", "2025"
        
        # Extrair valores numéricos com labels
        lines = text.split('\n')
        
        # Dicionário para acumular valores
        values = {
            "revenue_operational": 0,
            "revenue_events": 0,
            "tax": 0,
            "cmv": 0,
            "other_costs": 0,
            "payroll": 0,
            "admin": 0,
            "variable": 0,
            "financial": 0,
            "gross_result": 0,
            "intercompany_receivable": 0,
            "intercompany_payable": 0,
            "partner_distributions": 0,
            "net_result": 0
        }
        
        for line in lines:
            line_clean = line.strip().upper()
            
            # Receita
            if any(k in line_clean for k in ['RECEITA', 'FATURAMENTO', 'VENDAS']):
                val = self._extract_value(line)
                if 'EVENTO' in line_clean or 'SERVIÇO' in line_clean:
                    values["revenue_events"] = val
                else:
                    values["revenue_operational"] = val
            
            # Impostos
            elif any(k in line_clean for k in ['IMPOSTO', 'TAX', 'ISS', 'ICMS']):
                values["tax"] = abs(self._extract_value(line))
            
            # CMV
            elif any(k in line_clean for k in ['CMV', 'CUSTO MERCADORIA', 'COGS']):
                values["cmv"] = abs(self._extract_value(line))
            
            # Outros custos
            elif any(k in line_clean for k in ['OUTRO CUSTO', 'MATERIAL', 'INSUMO']):
                values["other_costs"] += abs(self._extract_value(line))
            
            # Folha
            elif any(k in line_clean for k in ['FOLHA', 'SALÁRIO', 'PAYROLL', 'PRO-LABORE']):
                values["payroll"] += abs(self._extract_value(line))
            
            # Admin
            elif any(k in line_clean for k in ['ADMINISTRATIVO', 'ADMIN', 'ESCRITÓRIO']):
                values["admin"] += abs(self._extract_value(line))
            
            # Variável
            elif any(k in line_clean for k in ['VARIÁVEL', 'VARIAVEL', 'MARKETING']):
                values["variable"] += abs(self._extract_value(line))
            
            # Financeiro
            elif any(k in line_clean for k in ['FINANCEIRO', 'JUROS', 'BANK']):
                values["financial"] += abs(self._extract_value(line))
            
            # Intercompany
            elif any(k in line_clean for k in ['INTERCOMPANY', 'STATUS', 'LA ORANA', 'ENTRE EMPRESA']):
                val = self._extract_value(line)
                if 'A RECEBER' in line_clean or 'RECEIVABLE' in line_clean:
                    values["intercompany_receivable"] = abs(val)
                elif 'A PAGAR' in line_clean or 'PAYABLE' in line_clean:
                    values["intercompany_payable"] = abs(val)
            
            # Distribuição sócios
            elif any(k in line_clean for k in ['DISTRIBUIÇÃO', 'DIVIDENDO', 'SÓCIO', 'PARTNER']):
                values["partner_distributions"] += abs(self._extract_value(line))
            
            # Resultado
            elif any(k in line_clean for k in ['RESULTADO', 'LUCRO', 'PREJUÍZO']):
                val = self._extract_value(line)
                if 'LIQUIDO' in line_clean or 'NET' in line_clean:
                    values["net_result"] = val
                elif 'BRUTO' in line_clean or 'GROSS' in line_clean:
                    values["gross_result"] = val
        
        # Calcular gross_result se não encontrado
        if values["gross_result"] == 0:
            values["gross_result"] = (
                values["revenue_operational"] + values["revenue_events"] - 
                values["tax"] - values["cmv"] - values["other_costs"]
            )
        
        # Verificar inconsistências
        inconsistencies = self._check_inconsistencies(values)
        
        record = FinancialRecord(
            company=company,
            month=month,
            year=year,
            **values,
            source_file=source_file,
            inconsistencies=inconsistencies
        )
        
        records.append(record)
        return records
    
    def parse_spreadsheet(self, filepath: str, company: str, sheet_name: str = None) -> List[FinancialRecord]:
        """
        Parse de planilha (CSV ou Excel).
        """
        records = []
        
        ext = Path(filepath).suffix.lower()
        
        if ext == '.csv':
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = self._row_to_record(row, company, filepath)
                    if record:
                        records.append(record)
        
        elif ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                df = pd.read_excel(filepath, sheet_name=sheet_name or 0)
                for _, row in df.iterrows():
                    record = self._row_to_record(row.to_dict(), company, filepath)
                    if record:
                        records.append(record)
            except ImportError:
                print("⚠️ pandas não instalado. Instale: pip install pandas openpyxl")
        
        return records
    
    def _extract_value(self, line: str) -> float:
        """Extrai valor monetário de uma linha."""
        # Remover caracteres não-numéricos exceto . e ,
        cleaned = re.sub(r'[^\d.,\-]', '', line)
        
        # Tentar encontrar número
        match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)', cleaned)
        if match:
            num_str = match.group(1)
            # Detectar se usa vírgula ou ponto como decimal
            if ',' in num_str and '.' in num_str:
                if num_str.rindex(',') > num_str.rindex('.'):
                    # Formato brasileiro: 1.234,56
                    num_str = num_str.replace('.', '').replace(',', '.')
                else:
                    # Formato americano: 1,234.56
                    num_str = num_str.replace(',', '')
            elif ',' in num_str:
                # Verificar se é separador de milhar ou decimal
                if len(num_str.split(',')[-1]) == 2:
                    num_str = num_str.replace(',', '.')
                else:
                    num_str = num_str.replace(',', '')
            
            try:
                return float(num_str)
            except:
                return 0.0
        
        return 0.0
    
    def _row_to_record(self, row: Dict, company: str, source_file: str) -> Optional[FinancialRecord]:
        """Converte linha de planilha em record normalizado."""
        
        # Mapear campos possíveis
        field_map = {
            "revenue_operational": ['revenue_operational', 'receita_operacional', 'faturamento', 'receita'],
            "revenue_events": ['revenue_events', 'receita_eventos', 'eventos'],
            "tax": ['tax', 'imposto', 'iss', 'icms'],
            "cmv": ['cmv', 'custo_mercadoria', 'insumos'],
            "other_costs": ['other_costs', 'outros_custos', 'material'],
            "payroll": ['payroll', 'folha', 'salarios'],
            "admin": ['admin', 'administrativo', 'despesa_adm'],
            "variable": ['variable', 'variavel', 'marketing'],
            "financial": ['financial', 'financeiro', 'juros'],
            "intercompany_receivable": ['intercompany_rec', 'status_rec', 'a_receber'],
            "intercompany_payable": ['intercompany_pay', 'status_pay', 'a_pagar'],
            "partner_distributions": ['partner_dist', 'distribuicao', 'dividendos'],
            "net_result": ['net_result', 'resultado_liquido', 'lucro_liquido']
        }
        
        values = {}
        for field, alternatives in field_map.items():
            values[field] = 0.0
            for alt in alternatives:
                if alt in row and row[alt]:
                    try:
                        val = str(row[alt]).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                        values[field] = float(val)
                        break
                    except:
                        pass
        
        # Detectar mês/ano
        month = "01"
        year = "2025"
        for key in row:
            if 'mes' in key.lower() or 'month' in key.lower():
                month_val = str(row[key])
                if month_val.isdigit() and 1 <= int(month_val) <= 12:
                    month = f"{int(month_val):02d}"
            if 'ano' in key.lower() or 'year' in key.lower():
                year_val = str(row[key])
                if year_val.isdigit() and len(year_val) == 4:
                    year = year_val
        
        # Calcular gross_result
        gross = (
            values.get("revenue_operational", 0) + values.get("revenue_events", 0) - 
            values.get("tax", 0) - values.get("cmv", 0) - values.get("other_costs", 0)
        )
        values["gross_result"] = gross
        
        # Verificar inconsistências
        inconsistencies = self._check_inconsistencies(values)
        
        return FinancialRecord(
            company=company,
            month=month,
            year=year,
            **values,
            source_file=source_file,
            inconsistencies=inconsistencies
        )
    
    def _check_inconsistencies(self, values: Dict) -> List[str]:
        """Verifica inconsistências nos valores."""
        issues = []
        
        # CMV > Receita
        total_revenue = values.get("revenue_operational", 0) + values.get("revenue_events", 0)
        cmv = values.get("cmv", 0)
        if cmv > total_revenue * 0.5:
            issues.append(f"CMV_ALTO: {cmv/total_revenue*100:.1f}% da receita")
        
        # Distribuição > Lucro
        net_result = values.get("net_result", 0)
        partner_dist = values.get("partner_distributions", 0)
        if net_result > 0 and partner_dist > net_result * 0.5:
            issues.append(f"DISTRIBUICAO_ALTA: {partner_dist/net_result*100:.1f}% do lucro")
        
        # Intercompany desbalanceado
        rec = values.get("intercompany_receivable", 0)
        pay = values.get("intercompany_payable", 0)
        if abs(rec - pay) > 50000:
            issues.append(f"INTERCOMPANY_DESBALANCEADO: Diferença de R$ {abs(rec-pay):,.0f}")
        
        # Lucro bruto negativo mas líquido positivo
        gross = values.get("gross_result", 0)
        if gross < 0 and net_result > 0:
            issues.append("RESULTADO_INCONSISTENTE: Bruto negativo, líquido positivo")
        
        return issues
    
    def generate_outputs(self) -> Dict:
        """Gera todos os outputs estruturados."""
        
        outputs = {
            "dre_opera_monthly": [],
            "dre_la_orana_monthly": [],
            "intercompany_monthly": [],
            "partner_withdrawals": [],
            "normalized_kpis": []
        }
        
        for record in self.records:
            # DRE por empresa
            dre_entry = {
                "company": record.company,
                "month": record.month,
                "year": record.year,
                "revenue_operational": record.revenue_operational,
                "revenue_events": record.revenue_events,
                "tax": record.tax,
                "cmv": record.cmv,
                "other_costs": record.other_costs,
                "payroll": record.payroll,
                "admin": record.admin,
                "variable": record.variable,
                "financial": record.financial,
                "gross_result": record.gross_result,
                "partner_distributions": record.partner_distributions,
                "net_result": record.net_result,
                "source_file": record.source_file,
                "inconsistencies": record.inconsistencies
            }
            
            if "OPERA" in record.company.upper() or "STATUS" in record.company.upper():
                outputs["dre_opera_monthly"].append(dre_entry)
            else:
                outputs["dre_la_orana_monthly"].append(dre_entry)
            
            # Intercompany
            if record.intercompany_receivable > 0 or record.intercompany_payable > 0:
                inter_entry = {
                    "company": record.company,
                    "month": record.month,
                    "year": record.year,
                    "receivable": record.intercompany_receivable,
                    "payable": record.intercompany_payable,
                    "net_position": record.intercompany_receivable - record.intercompany_payable,
                    "source_file": record.source_file
                }
                outputs["intercompany_monthly"].append(inter_entry)
            
            # Partner withdrawals
            if record.partner_distributions > 0:
                withdrawal_entry = {
                    "company": record.company,
                    "month": record.month,
                    "year": record.year,
                    "amount": record.partner_distributions,
                    "vs_net_result_pct": (record.partner_distributions / record.net_result * 100) if record.net_result != 0 else 0,
                    "source_file": record.source_file
                }
                outputs["partner_withdrawals"].append(withdrawal_entry)
        
        # KPIs normalizados
        for record in self.records:
            total_revenue = record.revenue_operational + record.revenue_events
            if total_revenue > 0:
                kpi_entry = {
                    "company": record.company,
                    "month": f"{record.year}-{record.month}",
                    "cmv_pct": round(record.cmv / total_revenue * 100, 2),
                    "payroll_pct": round(record.payroll / total_revenue * 100, 2),
                    "admin_pct": round(record.admin / total_revenue * 100, 2),
                    "gross_margin_pct": round(record.gross_result / total_revenue * 100, 2),
                    "net_margin_pct": round(record.net_result / total_revenue * 100, 2) if total_revenue > 0 else 0,
                    "intercompany_pct": round((record.intercompany_receivable + record.intercompany_payable) / total_revenue * 100, 2)
                }
                outputs["normalized_kpis"].append(kpi_entry)
        
        return outputs
    
    def save_outputs(self, outputs: Dict, output_dir: str = "data/processed"):
        """Salva todos os outputs."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        for name, data in outputs.items():
            filepath = Path(output_dir) / f"{name}.json"
            with open(filepath, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            saved_files.append(filepath)
            print(f"   💾 {filepath} ({len(data)} registros)")
        
        # Salvar metadata
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(self.records),
            "companies": list(set(r.company for r in self.records)),
            "periods": list(set(f"{r.year}-{r.month}" for r in self.records)),
            "inconsistencies_total": sum(len(r.inconsistencies) for r in self.records),
            "files_generated": [str(f) for f in saved_files]
        }
        
        meta_path = Path(output_dir) / "ingestion_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return saved_files
    
    def print_summary(self, outputs: Dict):
        """Imprime resumo da ingestão."""
        print("\n" + "=" * 70)
        print("📊 RESUMO DA INGESTÃO DE DADOS REAIS")
        print("=" * 70)
        
        print(f"\n📁 REGISTROS PROCESSADOS:")
        print(f"   Total: {len(self.records)}")
        print(f"   Opera/Status: {len([r for r in self.records if 'OPERA' in r.company.upper() or 'STATUS' in r.company.upper()])}")
        print(f"   La Orana: {len([r for r in self.records if 'LA ORANA' in r.company.upper()])}")
        
        print(f"\n💰 ANÁLISE FINANCEIRA:")
        total_revenue = sum(r.revenue_operational + r.revenue_events for r in self.records)
        total_costs = sum(r.cmv + r.other_costs + r.payroll + r.admin + r.variable + r.financial for r in self.records)
        total_profit = sum(r.net_result for r in self.records)
        total_intercompany = sum(r.intercompany_receivable + r.intercompany_payable for r in self.records)
        total_withdrawals = sum(r.partner_distributions for r in self.records)
        
        print(f"   Receita Total: R$ {total_revenue:,.0f}")
        print(f"   Custos Totais: R$ {total_costs:,.0f}")
        print(f"   Resultado Líquido: R$ {total_profit:,.0f}")
        print(f"   Intercompany: R$ {total_intercompany:,.0f}")
        print(f"   Distribuições Sócios: R$ {total_withdrawals:,.0f}")
        
        print(f"\n⚠️  INCONSISTÊNCIAS DETECTADAS:")
        total_issues = sum(len(r.inconsistencies) for r in self.records)
        print(f"   Total: {total_issues}")
        for r in self.records:
            if r.inconsistencies:
                print(f"   {r.company} {r.month}/{r.year}: {', '.join(r.inconsistencies)}")
        
        print(f"\n📊 OUTPUTS GERADOS:")
        for name, data in outputs.items():
            print(f"   {name}.json: {len(data)} registros")
        
        print("\n" + "=" * 70)


def run_real_data_ingestion(source_files: List[Tuple[str, str]] = None):
    """
    Executa ingestão completa de dados reais.
    
    Args:
        source_files: Lista de tuplas (filepath, company_name)
    """
    print("\n" + "=" * 70)
    print("📥 ORKESTRA REAL DATA INGESTION ENGINE")
    print("   Transformação de PDFs e Planilhas em Datasets Estruturados")
    print("=" * 70)
    
    engine = RealDataIngestionEngine()
    
    # Se não forneceu arquivos, mostrar exemplo
    if not source_files:
        print("\n⚠️  Nenhum arquivo fornecido.")
        print("   Exemplo de uso:")
        print("   source_files = [")
        print('       ("data/pdf/status_jan_abr_2025.pdf", "OPERA"),')
        print('       ("data/sheets/la_orana_2024.xlsx", "LA ORANA"),')
        print("   ]")
        print("\n   Para PDFs, garanta que o texto foi extraído (OCR ou text layer)")
        return []
    
    # Processar cada arquivo
    for filepath, company in source_files:
        print(f"\n📂 Processando: {filepath} ({company})")
        
        if not Path(filepath).exists():
            print(f"   ❌ Arquivo não encontrado: {filepath}")
            continue
        
        ext = Path(filepath).suffix.lower()
        
        if ext == '.pdf':
            # Para PDFs, precisamos de texto extraído
            # Aqui assumimos que há um arquivo .txt com o mesmo nome
            txt_path = filepath.replace('.pdf', '.txt')
            if Path(txt_path).exists():
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                records = engine.parse_pdf_text(text, company, filepath)
                engine.records.extend(records)
                print(f"   ✅ {len(records)} registros extraídos")
            else:
                print(f"   ⚠️  Arquivo .txt não encontrado: {txt_path}")
                print(f"      Extraia o texto do PDF primeiro")
        
        elif ext in ['.csv', '.xlsx', '.xls']:
            records = engine.parse_spreadsheet(filepath, company)
            engine.records.extend(records)
            print(f"   ✅ {len(records)} registros extraídos")
        
        else:
            print(f"   ❌ Formato não suportado: {ext}")
    
    if not engine.records:
        print("\n❌ Nenhum registro processado.")
        return []
    
    # Gerar outputs
    print("\n📊 Gerando datasets estruturados...")
    outputs = engine.generate_outputs()
    
    # Salvar
    print("\n💾 Salvando arquivos...")
    saved = engine.save_outputs(outputs)
    
    # Imprimir resumo
    engine.print_summary(outputs)
    
    return saved


if __name__ == "__main__":
    import sys
    
    # Exemplo: python real_data_ingestion.py arquivo.pdf OPERA
    if len(sys.argv) >= 3:
        files = [(sys.argv[1], sys.argv[2])]
        run_real_data_ingestion(files)
    else:
        print("Uso: python real_data_ingestion.py <arquivo> <empresa>")
        print("     python real_data_ingestion.py status_2024.pdf OPERA")
