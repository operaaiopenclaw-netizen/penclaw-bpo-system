# data_processor_real.py - Orkestra Real Financial Data Processor
# Processa dados financeiros reais de STATUS/Opera e LA ORANA

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MonthlyRecord:
    """Registro mensal de DRE."""
    company: str          # "STATUS" ou "LA_ORANA"
    month: int            # 1-12
    year: int             # 2024 ou 2025
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
    partner_withdrawals: float
    net_result: float
    source_file: str
    inconsistencies: List[str]


@dataclass
class IntercompanyFlow:
    """Fluxo intercompany."""
    month: int
    year: int
    from_company: str
    to_company: str
    amount: float
    description: str


@dataclass  
class PartnerWithdrawal:
    """Retirada de sócios."""
    month: int
    year: int
    company: str
    amount: float
    partner_name: str
    distribution_type: str  # "PRO-LABORE", "DIVIDENDO", "RETIRADA"


class RealDataProcessor:
    """
    Processador de dados financeiros reais.
    Lê arquivos de STATUS/Opera e LA ORANA e estrutura datasets.
    """
    
    # Mapeamento de meses PT para número
    MONTH_MAP = {
        'janeiro': 1, 'jan': 1, 'fevereiro': 2, 'fev': 2,
        'março': 3, 'mar': 3, 'abril': 4, 'abr': 4,
        'maio': 5, 'mai': 5, 'junho': 6, 'jun': 6,
        'julho': 7, 'jul': 7, 'agosto': 8, 'ago': 8,
        'setembro': 9, 'set': 9, 'outubro': 10, 'out': 10,
        'novembro': 11, 'nov': 11, 'dezembro': 12, 'dez': 12
    }
    
    def __init__(self):
        self.status_records: List[MonthlyRecord] = []
        self.la_orana_records: List[MonthlyRecord] = []
        self.intercompany_flows: List[IntercompanyFlow] = []
        self.withdrawals: List[PartnerWithdrawal] = []
        self.inconsistencies: List[Dict] = []
    
    def detect_company(self, filename: str, content: str) -> str:
        """
        Detecta se arquivo é de STATUS/Opera ou LA ORANA.
        """
        filename_lower = filename.lower()
        content_lower = content.lower()[:2000]  # Primeiros 2000 chars
        
        # Keywords para STATUS/Opera
        status_keywords = ['status', 'opera', 'locação', 'aluguel', 'espaço', 'venue']
        
        # Keywords para LA ORANA
        la_orana_keywords = ['la orana', 'catering', 'alimentação', 'buffet', 'cozinha']
        
        status_score = sum(1 for kw in status_keywords if kw in filename_lower or kw in content_lower)
        la_orana_score = sum(1 for kw in la_orana_keywords if kw in filename_lower or kw in content_lower)
        
        if status_score > la_orana_score:
            return "STATUS"
        elif la_orana_score > status_score:
            return "LA_ORANA"
        else:
            # Padrão: se nome tem "status" ou "opera"
            if any(x in filename_lower for x in ['status', 'opera']):
                return "STATUS"
            return "LA_ORANA"
    
    def extract_month_year(self, filename: str, content: str) -> Tuple[int, int]:
        """
        Extrai mês e ano do nome do arquivo ou conteúdo.
        """
        # Procurar no nome primeiro
        filename_lower = filename.lower()
        
        # Ano
        year_match = re.search(r'20(24|25)', filename_lower)
        if not year_match:
            year_match = re.search(r'20(24|25)', content.lower()[:1000])
        year = int(year_match.group(0)) if year_match else 2024
        
        # Mês
        month = 1
        for month_name, month_num in self.MONTH_MAP.items():
            if month_name in filename_lower:
                month = month_num
                break
        
        # Se não encontrou no nome, procurar no conteúdo
        if month == 1:
            content_lower = content.lower()[:2000]
            for month_name, month_num in self.MONTH_MAP.items():
                if month_name in content_lower:
                    month = month_num
                    break
        
        return month, year
    
    def parse_value(self, text: str) -> float:
        """Extrai valor monetário de texto."""
        # Remover R$ e espaços
        clean = text.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        
        # Encontrar número
        match = re.search(r'-?\d+\.?\d*', clean)
        if match:
            try:
                return float(match.group())
            except:
                return 0.0
        return 0.0
    
    def identify_line_type(self, line: str) -> Tuple[str, float]:
        """
        Identifica tipo de linha e extrai valor.
        Retorna (tipo, valor).
        """
        line_lower = line.lower().strip()
        value = self.parse_value(line)
        
        # Receita operacional
        if any(k in line_lower for k in ['receita bruta', 'faturamento', 'receita operacional']):
            return ('revenue_operational', value)
        
        # Receita de eventos
        if any(k in line_lower for k in ['evento', 'serviço', 'prestação']):
            return ('revenue_events', value)
        
        # Impostos
        if any(k in line_lower for k in ['imposto', 'iss', 'icms', 'pis', 'cofins']):
            return ('tax', abs(value))
        
        # CMV
        if any(k in line_lower for k in ['cmv', 'custo mercadoria', 'insumo']):
            return ('cmv', abs(value))
        
        # Outros custos
        if any(k in line_lower for k in ['material', 'outro custo', 'despesa']):
            return ('other_costs', abs(value))
        
        # Folha
        if any(k in line_lower for k in ['folha', 'salário', 'pró-labore', 'pro-labore']):
            return ('payroll', abs(value))
        
        # Admin
        if any(k in line_lower for k in ['administrativo', 'admin']):
            return ('admin', abs(value))
        
        # Variável
        if any(k in line_lower for k in ['variável', 'marketing', 'comissão']):
            return ('variable', abs(value))
        
        # Financeiro
        if any(k in line_lower for k in ['financeiro', 'banco', 'juros']):
            return ('financial', abs(value))
        
        # Intercompany
        if any(k in line_lower for k in ['status', 'la orana', 'intercompany']):
            if 'a receber' in line_lower or 'receivable' in line_lower:
                return ('intercompany_receivable', value)
            elif 'a pagar' in line_lower or 'payable' in line_lower:
                return ('intercompany_payable', abs(value))
        
        # Distribuição sócios
        if any(k in line_lower for k in ['dividendo', 'distribuição', 'sócio', 'retirada']):
            return ('partner_withdrawals', abs(value))
        
        # Resultado
        if 'lucro' in line_lower or 'resultado' in line_lower:
            if 'líquido' in line_lower or 'net' in line_lower or 'liquido' in line_lower:
                return ('net_result', value)
            elif 'bruto' in line_lower or 'gross' in line_lower:
                return ('gross_result', value)
        
        return ('unknown', 0.0)
    
    def process_pdf_text(self, filename: str, text_content: str) -> Dict:
        """
        Processa texto extraído de PDF.
        """
        company = self.detect_company(filename, text_content)
        month, year = self.extract_month_year(filename, text_content)
        
        # Inicializar valores
        record = {
            'company': company,
            'month': month,
            'year': year,
            'revenue_operational': 0.0,
            'revenue_events': 0.0,
            'tax': 0.0,
            'cmv': 0.0,
            'other_costs': 0.0,
            'payroll': 0.0,
            'admin': 0.0,
            'variable': 0.0,
            'financial': 0.0,
            'gross_result': 0.0,
            'intercompany_receivable': 0.0,
            'intercompany_payable': 0.0,
            'partner_withdrawals': 0.0,
            'net_result': 0.0,
            'source_file': filename,
            'inconsistencies': []
        }
        
        # Processar linhas
        lines = text_content.split('\n')
        intercompany_lines = []
        withdrawal_lines = []
        
        for line in lines:
            line_type, value = self.identify_line_type(line)
            
            if line_type == 'unknown':
                continue
            
            # Acumular valores (alguns podem aparecer múltiplas vezes)
            if line_type in record:
                if line_type in ['revenue_operational', 'revenue_events', 'gross_result', 'net_result', 'intercompany_receivable']:
                    # Pegar maior valor (evitar duplicar)
                    record[line_type] = max(record[line_type], value)
                else:
                    # Custos: somar
                    record[line_type] += abs(value)
            
            # Capture intercompany details
            if line_type.startswith('intercompany'):
                intercompany_lines.append({'type': line_type, 'value': value, 'line': line.strip()})
            
            # Capture withdrawals
            if line_type == 'partner_withdrawals':
                withdrawal_lines.append({'value': value, 'line': line.strip()})
        
        # Calcular gross se não existir
        if record['gross_result'] == 0:
            record['gross_result'] = (
                record['revenue_operational'] + record['revenue_events'] - 
                record['tax'] - record['cmv'] - record['other_costs']
            )
        
        # Verificar inconsistências
        record['inconsistencies'] = self._check_record_consistency(record)
        
        # Criar registro
        monthly_record = MonthlyRecord(**record)
        
        # Criar intercompany flows
        flows = []
        for ic in intercompany_lines:
            if ic['value'] != 0:
                to_company = "LA_ORANA" if company == "STATUS" else "STATUS"
                flows.append(IntercompanyFlow(
                    month=month,
                    year=year,
                    from_company=company if ic['type'] == 'intercompany_payable' else to_company,
                    to_company=to_company if ic['type'] == 'intercompany_payable' else company,
                    amount=abs(ic['value']),
                    description=ic['line'][:100]
                ))
        
        # Criar withdrawals
        withdrawals = []
        for wd in withdrawal_lines:
            withdrawals.append(PartnerWithdrawal(
                month=month,
                year=year,
                company=company,
                amount=abs(wd['value']),
                partner_name="Sócio",  # Genérico se não identificado
                distribution_type="DISTRIBUICAO"
            ))
        
        return {
            'record': monthly_record,
            'intercompany_flows': flows,
            'withdrawals': withdrawals
        }
    
    def _check_record_consistency(self, record: Dict) -> List[str]:
        """Verifica inconsistências no registro."""
        issues = []
        
        # CMV > 50% receita
        total_revenue = record['revenue_operational'] + record['revenue_events']
        if total_revenue > 0 and record['cmv'] > total_revenue * 0.5:
            issues.append(f"CMV_ALTO: {record['cmv']/total_revenue*100:.1f}% da receita")
        
        # Distribuição > lucro
        if record['net_result'] > 0 and record['partner_withdrawals'] > record['net_result']:
            issues.append(f"DISTRIBUICAO_MAIOR_QUE_LUCRO")
        
        # Resultado bruto positivo, líquido negativo
        if record['gross_result'] > 0 and record['net_result'] < 0:
            issues.append("BRUTO_POSITIVO_LIQUIDO_NEGATIVO")
        
        # Intercompany desbalanceado
        if abs(record['intercompany_receivable'] - record['intercompany_payable']) > 10000:
            issues.append("INTERCOMPANY_DESBALANCEADO")
        
        return issues
    
    def add_record(self, data: Dict):
        """Adiciona registro processado."""
        if data['record'].company == "STATUS":
            self.status_records.append(data['record'])
        else:
            self.la_orana_records.append(data['record'])
        
        self.intercompany_flows.extend(data['intercompany_flows'])
        self.withdrawals.extend(data['withdrawals'])
    
    def generate_outputs(self) -> Dict:
        """Gera todos os datasets estruturados."""
        
        # DRE STATUS
        dre_status = []
        for r in self.status_records:
            dre_status.append({
                "company": r.company,
                "month": r.month,
                "year": r.year,
                "revenue_operational": r.revenue_operational,
                "revenue_events": r.revenue_events,
                "tax": r.tax,
                "cmv": r.cmv,
                "other_costs": r.other_costs,
                "payroll": r.payroll,
                "admin": r.admin,
                "variable": r.variable,
                "financial": r.financial,
                "gross_result": r.gross_result,
                "intercompany_receivable": r.intercompany_receivable,
                "intercompany_payable": r.intercompany_payable,
                "partner_withdrawals": r.partner_withdrawals,
                "net_result": r.net_result,
                "source_file": r.source_file,
                "inconsistencies": r.inconsistencies
            })
        
        # DRE LA ORANA
        dre_la_orana = []
        for r in self.la_orana_records:
            dre_la_orana.append({
                "company": r.company,
                "month": r.month,
                "year": r.year,
                "revenue_operational": r.revenue_operational,
                "revenue_events": r.revenue_events,
                "tax": r.tax,
                "cmv": r.cmv,
                "other_costs": r.other_costs,
                "payroll": r.payroll,
                "admin": r.admin,
                "variable": r.variable,
                "financial": r.financial,
                "gross_result": r.gross_result,
                "intercompany_receivable": r.intercompany_receivable,
                "intercompany_payable": r.intercompany_payable,
                "partner_withdrawals": r.partner_withdrawals,
                "net_result": r.net_result,
                "source_file": r.source_file,
                "inconsistencies": r.inconsistencies
            })
        
        # Intercompany Flow
        intercompany = []
        for f in self.intercompany_flows:
            intercompany.append({
                "month": f.month,
                "year": f.year,
                "from_company": f.from_company,
                "to_company": f.to_company,
                "amount": f.amount,
                "description": f.description
            })
        
        # Withdrawals
        withdrawals = []
        for w in self.withdrawals:
            withdrawals.append({
                "month": w.month,
                "year": w.year,
                "company": w.company,
                "amount": w.amount,
                "partner_name": w.partner_name,
                "distribution_type": w.distribution_type
            })
        
        return {
            "dre_status_monthly": dre_status,
            "dre_la_orana_monthly": dre_la_orana,
            "intercompany_flow": intercompany,
            "withdrawals": withdrawals
        }
    
    def save_outputs(self, output_dir: str = "data/real_financial"):
        """Salva datasets em arquivos."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        data = self.generate_outputs()
        
        saved_files = []
        for name, dataset in data.items():
            filepath = Path(output_dir) / f"{name}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            saved_files.append(str(filepath))
            print(f"   💾 {filepath} ({len(dataset)} registros)")
        
        # Metadata
        metadata = {
            "processed_at": datetime.now().isoformat(),
            "status_records": len(self.status_records),
            "la_orana_records": len(self.la_orana_records),
            "intercompany_flows": len(self.intercompany_flows),
            "withdrawals": len(self.withdrawals),
            "total_inconsistencies": sum(len(r.inconsistencies) for r in self.status_records + self.la_orana_records)
        }
        
        meta_path = Path(output_dir) / "processing_metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return saved_files
    
    def print_summary(self):
        """Imprime resumo do processamento."""
        print("\n" + "=" * 70)
        print("📊 RESUMO DO PROCESSAMENTO DE DADOS REAIS")
        print("=" * 70)
        
        print(f"\n📁 REGISTROS POR EMPRESA:")
        print(f"   STATUS/Opera: {len(self.status_records)} meses")
        print(f"   LA ORANA: {len(self.la_orana_records)} meses")
        
        if self.status_records:
            print(f"\n💰 STATUS/Opera:")
            total_rev = sum(r.revenue_operational + r.revenue_events for r in self.status_records)
            total_cost = sum(r.cmv + r.payroll + r.admin for r in self.status_records)
            print(f"   Receita Total: R$ {total_rev:,.0f}")
            print(f"   Custos: R$ {total_cost:,.0f}")
            print(f"   Resultado: R$ {sum(r.net_result for r in self.status_records):,.0f}")
        
        if self.la_orana_records:
            print(f"\n🍽️  LA ORANA:")
            total_rev = sum(r.revenue_operational + r.revenue_events for r in self.la_orana_records)
            total_cmv = sum(r.cmv for r in self.la_orana_records)
            print(f"   Receita Total: R$ {total_rev:,.0f}")
            print(f"   CMV: R$ {total_cmv:,.0f}")
            print(f"   Resultado: R$ {sum(r.net_result for r in self.la_orana_records):,.0f}")
        
        if self.intercompany_flows:
            total_flow = sum(f.amount for f in self.intercompany_flows)
            print(f"\n🔄 FLUXO INTERCOMPANY:")
            print(f"   Transações: {len(self.intercompany_flows)}")
            print(f"   Valor Total: R$ {total_flow:,.0f}")
        
        if self.withdrawals:
            total_wd = sum(w.amount for w in self.withdrawals)
            print(f"\n💸 DISTRIBUIÇÕES SÓCIOS:")
            print(f"   Registros: {len(self.withdrawals)}")
            print(f"   Valor Total: R$ {total_wd:,.0f}")
        
        # Inconsistências
        all_inconsistencies = []
        for r in self.status_records + self.la_orana_records:
            if r.inconsistencies:
                all_inconsistencies.append({
                    "company": r.company,
                    "month": r.month,
                    "year": r.year,
                    "issues": r.inconsistencies
                })
        
        if all_inconsistencies:
            print(f"\n⚠️  INCONSISTÊNCIAS DETECTADAS ({len(all_inconsistencies)} registros):")
            for inc in all_inconsistencies:
                print(f"   {inc['company']} {inc['month']:02d}/{inc['year']}: {', '.join(inc['issues'])}")
        else:
            print(f"\n✅ Nenhuma inconsistência detectada")
        
        print("\n" + "=" * 70)


# Função helper para processar arquivos

def process_real_files(file_list: List[Tuple[str, str]]):
    """
    Processa lista de arquivos reais.
    
    Args:
        file_list: Lista de tuplas (filepath, text_content)
    """
    processor = RealDataProcessor()
    
    print(f"\n📂 Processando {len(file_list)} arquivos...\n")
    
    for filepath, content in file_list:
        print(f"   Processando: {filepath}")
        
        if not content:
            print(f"   ⚠️  Conteúdo vazio")
            continue
        
        try:
            result = processor.process_pdf_text(filepath, content)
            processor.add_record(result)
            print(f"   ✅ {result['record'].company} - {result['record'].month:02d}/{result['record'].year}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    # Gerar outputs
    print("\n📊 Gerando datasets...")
    saved = processor.save_outputs()
    
    # Imprimir resumo
    processor.print_summary()
    
    return saved


if __name__ == "__main__":
    # Exemplo de uso
    print("Orkestra Real Data Processor - Pronto para receber arquivos")
    print("\nUso:")
    print("  from data_processor_real import process_real_files")
    print("  files = [")
    print('      ("data/real_financial/2024/status_jan_2024.pdf", "<conteudo_extraido>"),')
    print("  ]")
    print("  process_real_files(files)")
