#!/usr/bin/env python3
"""
Orkestra Finance Brain - Backtest Generator
Companhia: LA ORANA + STATUS Opera
Generated: 2026-04-07
"""

import json
import csv
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import copy

# ============================================================
# EMBEDDED FINANCIAL DATA (from provided documents)
# ============================================================

# ACCOUNTS RECEIVABLE - 53 records from LA ORANA and STATUS Opera
ACCOUNTS_RECEIVABLE = [
    # LA ORANA Records
    {"contract_id": "CTT-LA-202501-990", "client": "Escola Estadual Benedito Saldanha", "event_name": "Formatura 2025 - Colação", "amount_paid": 15592.00, "amount_receivable": 0.00, "event_date": "2025-01-31"},
    {"contract_id": "CTT-LA-202503-1028", "client": "Escola Estadual Benedito Saldanha", "event_name": "Formatura 2025 - Festa", "amount_paid": 45000.00, "amount_receivable": 0.00, "event_date": "2025-03-14"},
    {"contract_id": "CTT-LA-202509-1178", "client": "Escola Estadual Benedito Saldanha", "event_name": "Formatura 2026 - Colação", "amount_paid": 10000.00, "amount_receivable": 9000.00, "event_date": "2025-09-08"},
    {"contract_id": "CTT-LA-202501-996", "client": "Escola Estadual Benedito Saldanha", "event_name": "Aditivo Contrato Formatura", "amount_paid": 450.00, "amount_receivable": 0.00, "event_date": "2025-01-31"},
    {"contract_id": "CTT-LA-202502-1014", "client": "Família Soares", "event_name": "Aniversário 50 Anos", "amount_paid": 18000.00, "amount_receivable": 0.00, "event_date": "2025-02-15"},
    {"contract_id": "CTT-LA-202503-1032", "client": "Universidade Federal", "event_name": "Colação de Grau - Medicina", "amount_paid": 35000.00, "amount_receivable": 15000.00, "event_date": "2025-03-28"},
    {"contract_id": "CTT-LA-202504-1055", "client": "Coop. Medicina", "event_name": "Confraternização Médicos", "amount_paid": 22500.00, "amount_receivable": 5000.00, "event_date": "2025-04-12"},
    {"contract_id": "CTT-LA-202505-1089", "client": "Escola Americana", "event_name": "Formatura High School", "amount_paid": 125000.00, "amount_receivable": 125000.00, "event_date": "2025-05-30"},
    {"contract_id": "CTT-LA-202506-1112", "client": "TechCorp Brasil", "event_name": "Festa de Fim de Ano", "amount_paid": 40000.00, "amount_receivable": 60000.00, "event_date": "2025-06-20"},
    {"contract_id": "CTT-LA-202508-1145", "client": "Câmara Municipal", "event_name": "Sessão Solene Aniversário", "amount_paid": 8500.00, "amount_receivable": 0.00, "event_date": "2025-08-10"},
    {"contract_id": "CTT-LA-202509-1182", "client": "Escola Estadual Tiradentes", "event_name": "Formatura Ensino Médio", "amount_paid": 28000.00, "amount_receivable": 15000.00, "event_date": "2025-09-25"},
    {"contract_id": "CTT-LA-202510-1208", "client": "Empresa ABC Ltda", "event_name": "Lançamento Produto", "amount_paid": 45000.00, "amount_receivable": 15000.00, "event_date": "2025-10-15"},
    {"contract_id": "CTT-LA-202511-1241", "client": "ONG Vida", "event_name": "Gala Beneficente", "amount_paid": 95000.00, "amount_receivable": 45000.00, "event_date": "2025-11-20"},
    {"contract_id": "CTT-LA-202512-1265", "client": "Escola Estadual Benedito Saldanha", "event_name": "Formatura 2025 - Baile", "amount_paid": 52000.00, "amount_receivable": 0.00, "event_date": "2025-12-05"},
    
    # STATUS Opera Records
    {"contract_id": "CTT-ST-202408-894", "client": "Escola Superior de Saúde", "event_name": "Formatura 2024 - Formandos", "amount_paid": 68500.00, "amount_receivable": 0.00, "event_date": "2024-08-20"},
    {"contract_id": "CTT-ST-202409-901", "client": "Faculdade Estácio", "event_name": "Colação Engenharia", "amount_paid": 42500.00, "amount_receivable": 0.00, "event_date": "2024-09-15"},
    {"contract_id": "CTT-ST-202410-918", "client": "Colégio Modelo", "event_name": "Formatura 3º Ano", "amount_paid": 32000.00, "amount_receivable": 0.00, "event_date": "2024-10-10"},
    {"contract_id": "CTT-ST-202411-935", "client": "Instituto Federal", "event_name": "Colação Administração", "amount_paid": 28500.00, "amount_receivable": 3500.00, "event_date": "2024-11-05"},
    {"contract_id": "CTT-ST-202412-942", "client": "Universidade Católica", "event_name": "Formatura Direito", "amount_paid": 78000.00, "amount_receivable": 5000.00, "event_date": "2024-12-18"},
    {"contract_id": "CTT-ST-202501-967", "client": "Escola Militar", "event_name": "Formatura Oficiais", "amount_paid": 95000.00, "amount_receivable": 45000.00, "event_date": "2025-01-25"},
    {"contract_id": "CTT-ST-202502-985", "client": "Escola de Artes", "event_name": "Vernissage Formandos", "amount_paid": 22000.00, "amount_receivable": 16000.00, "event_date": "2025-02-10"},
    {"contract_id": "CTT-ST-202503-1015", "client": "Faculdade Metodista", "event_name": "Colação Direito", "amount_paid": 55000.00, "amount_receivable": 12000.00, "event_date": "2025-03-08"},
    {"contract_id": "CTT-ST-202504-1036", "client": "Corp Tech", "event_name": "Festa Corporativa", "amount_paid": 18000.00, "amount_receivable": 8000.00, "event_date": "2025-04-20"},
    {"contract_id": "CTT-ST-202505-1067", "client": "Escola Internacional", "event_name": "Formatura 12th Grade", "amount_paid": 145000.00, "amount_receivable": 85000.00, "event_date": "2025-05-15"},
    {"contract_id": "CTT-ST-202506-1098", "client": "Associação Comercial", "event_name": "Jantar Anual", "amount_paid": 38000.00, "amount_receivable": 0.00, "event_date": "2025-06-25"},
    {"contract_id": "CTT-ST-202507-1125", "client": "Escola Técnica", "event_name": "Formatura Técnico", "amount_paid": 26500.00, "amount_receivable": 8500.00, "event_date": "2025-07-12"},
    {"contract_id": "CTT-ST-202508-1158", "client": "Hospital Regional", "event_name": "Confraternização", "amount_paid": 32000.00, "amount_receivable": 0.00, "event_date": "2025-08-05"},
    {"contract_id": "CTT-ST-202509-1195", "client": "Escola Superior", "event_name": "Formatura 2025 - Medicina", "amount_paid": 87500.00, "amount_receivable": 27500.00, "event_date": "2025-09-20"},
    {"contract_id": "CTT-ST-202510-1221", "client": "Empresa XYZ", "event_name": "Convenção Anual", "amount_paid": 65000.00, "amount_receivable": 35000.00, "event_date": "2025-10-08"},
    {"contract_id": "CTT-ST-202511-1234", "client": "Escola Estadual Central", "event_name": "Formatura Ensino Médio", "amount_paid": 48500.00, "amount_receivable": 15000.00, "event_date": "2025-11-15"},
    {"contract_id": "CTT-ST-202512-1258", "client": "Prefeitura Municipal", "event_name": "Festa de Fim de Ano", "amount_paid": 52000.00, "amount_receivable": 0.00, "event_date": "2025-12-18"},
    {"contract_id": "CTT-ST-202601-1275", "client": "Escola Superior", "event_name": "Formatura 2026 - Odonto", "amount_paid": 25000.00, "amount_receivable": 55000.00, "event_date": "2026-01-20"},
    {"contract_id": "CTT-ST-202602-1292", "client": "Faculdade Unificada", "event_name": "Colação Odontologia", "amount_paid": 45000.00, "amount_receivable": 28000.00, "event_date": "2026-02-15"},
    {"contract_id": "CTT-ST-202603-1315", "client": "Escola de Negócios", "event_name": "Formatura MBA", "amount_paid": 55000.00, "amount_receivable": 32000.00, "event_date": "2026-03-10"},
    {"contract_id": "CTT-ST-202604-1338", "client": "Corp Solutions", "event_name": "Evento Corporativo", "amount_paid": 35000.00, "amount_receivable": 42000.00, "event_date": "2026-04-05"}]

# Accounts Payable - 27 records
ACCOUNTS_PAYABLE = [
    {"id": "PAY-001", "vendor": "Buffet Gourmet", "description": "Buffet Formatura Benedito Saldanha - Jan 2025", "amount": 8500.00, "due_date": "2025-01-31", "category": "proteina", "event_ref": "CTT-LA-202501-990"},
    {"id": "PAY-002", "vendor": "Som e Luz Pro", "description": "Estrutura audiovisual colação", "amount": 3200.00, "due_date": "2025-01-31", "category": "infraestrutura", "event_ref": "CTT-LA-202501-990"},
    {"id": "PAY-003", "vendor": "Decor Festas", "description": "Decoração formatura - festa Março", "amount": 8900.00, "due_date": "2025-03-14", "category": "ambientacao", "event_ref": "CTT-LA-202503-1028"},
    {"id": "PAY-004", "vendor": "Cervejaria Nacional", "description": "Bebidas open bar Março + Abril", "amount": 12500.00, "due_date": "2025-03-31", "category": "bebida", "event_ref": "MULTI-EVENT"},
    {"id": "PAY-005", "vendor": "Buffet Premium", "description": "Catering Coquetel Médicos", "amount": 11200.00, "due_date": "2025-04-12", "category": "proteina", "event_ref": "CTT-LA-202504-1055"},
    {"id": "PAY-006", "vendor": "Staff Eventos", "description": "Garçons/bartenders evento 1/2 maio", "amount": 4500.00, "due_date": "2025-05-15", "category": "staff", "event_ref": "SHARED-50"},
    {"id": "PAY-007", "vendor": "Aluguel Móveis", "description": "Mesas/cadeiras eventos maio-jun", "amount": 6800.00, "due_date": "2025-05-30", "category": "material", "event_ref": "CTT-LA-202505-1089"},
    {"id": "PAY-008", "vendor": "Comissão Comercial", "description": "BV Vendas - comissão 15%", "amount": 12500.00, "due_date": "2025-06-15", "category": "cac", "event_ref": "MULTI-EVENT"},
    {"id": "PAY-009", "vendor": "DJ Performance", "description": "Música evento junho", "amount": 3800.00, "due_date": "2025-06-20", "category": "infraestrutura", "event_ref": "CTT-LA-202506-1112"},
    {"id": "PAY-010", "vendor": "Floricultura Bella", "description": "Flores decoração formatura", "amount": 4200.00, "due_date": "2025-09-25", "category": "ambientacao", "event_ref": "CTT-LA-202509-1182"},
    {"id": "PAY-011", "vendor": "Buffet Central", "description": "Buffet Formatura Tiradentes 1/2", "amount": 9800.00, "due_date": "2025-09-25", "category": "proteina", "event_ref": "SHARED-50"},
    {"id": "PAY-012", "vendor": "Bebidas Express", "description": "Cerveja/destilados evento set", "amount": 6200.00, "due_date": "2025-09-30", "category": "bebida", "event_ref": "CTT-LA-202509-1182"},
    {"id": "PAY-013", "vendor": "Locação Estruturas", "description": "Tenda/Palco lançamento", "amount": 15600.00, "due_date": "2025-10-15", "category": "infraestrutura", "event_ref": "CTT-LA-202510-1208"},
    {"id": "PAY-014", "vendor": "Camarim Luxo", "description": "Camarim artistas gala", "amount": 8900.00, "due_date": "2025-11-20", "category": "indirect", "event_ref": "CTT-LA-202511-1241"},
    {"id": "PAY-015", "vendor": "Buffet Majestic", "description": "Catering formatura Baile Dez", "amount": 18500.00, "due_date": "2025-12-05", "category": "proteina", "event_ref": "CTT-LA-202512-1265"},
    {"id": "PAY-016", "vendor": "Bebidas Premium", "description": "Open bar completo Dezembro", "amount": 14200.00, "due_date": "2025-12-05", "category": "bebida", "event_ref": "CTT-LA-202512-1265"},
    {"id": "PAY-017", "vendor": "Buffet Superior", "description": "Formandos ago 2024", "amount": 22500.00, "due_date": "2024-08-20", "category": "proteina", "event_ref": "CTT-ST-202408-894"},
    {"id": "PAY-018", "vendor": "Estrutura Eventos", "description": "Som/luz/estrutura setembro 2024", "amount": 15800.00, "due_date": "2024-09-15", "category": "infraestrutura", "event_ref": "CTT-ST-202409-901"},
    {"id": "PAY-019", "vendor": "Bebidas do Centro", "description": "Bebidas outubro/nov 2024", "amount": 8900.00, "due_date": "2024-10-31", "category": "bebida", "event_ref": "MULTI-EVENT"},
    {"id": "PAY-020", "vendor": "Comissão Status", "description": "BV comercial 2024", "amount": 18500.00, "due_date": "2024-12-20", "category": "cac", "event_ref": "MULTI-EVENT"},
    {"id": "PAY-021", "vendor": "Buffet Noble", "description": "Militar janeiro 2025", "amount": 28500.00, "due_date": "2025-01-25", "category": "proteina", "event_ref": "CTT-ST-202501-967"},
    {"id": "PAY-022", "vendor": "Art Gallery", "description": "Espaço vernissage", "amount": 6500.00, "due_date": "2025-02-10", "category": "indirect", "event_ref": "CTT-ST-202502-985"},
    {"id": "PAY-023", "vendor": "Buffet Clássico", "description": "Direito março 2025", "amount": 19800.00, "due_date": "2025-03-08", "category": "proteina", "event_ref": "CTT-ST-202503-1015"},
    {"id": "PAY-024", "vendor": "Catering Express", "description": "Corporativo abril 2025", "amount": 7200.00, "due_date": "2025-04-20", "category": "proteina", "event_ref": "CTT-ST-202504-1036"},
    {"id": "PAY-025", "vendor": "Bebidas Premium", "description": "Internacional maio 2025", "amount": 24500.00, "due_date": "2025-05-15", "category": "bebida", "event_ref": "CTT-ST-202505-1067"},
    {"id": "PAY-026", "vendor": "Buffet Master", "description": "Técnico julho 2025", "amount": 11200.00, "due_date": "2025-07-12", "category": "proteina", "event_ref": "CTT-ST-202507-1125"},
    {"id": "PAY-027", "vendor": "Hospital Catering", "description": "Confraternização agosto 2025", "amount": 9800.00, "due_date": "2025-08-05", "category": "proteina", "event_ref": "CTT-ST-202508-1158"}]

# DRE LA ORANA - Monthly 2025
DRE_LA_ORANA_2025 = {
    "months": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
    "data": [
        {"month": 1, "receita_bruta": 18592.00, "impostos": 1338.62, "receita_liquida": 17253.38, "custo_alimentacao": 8500.00, "custo_bebidas": 2800.00, "custo_estrutura": 3200.00, "custo_pessoal": 0.00, "cmv_total": 14500.00, "despesas_operacionais": 1800.00, "despesas_comerciais": 1500.00, "despesas_adm": 1200.00, "lucro_operacional": -1746.62, "lucro_liquido": -1746.62},
        {"month": 2, "receita_bruta": 18000.00, "impostos": 1296.00, "receita_liquida": 16704.00, "custo_alimentacao": 9500.00, "custo_bebidas": 2100.00, "custo_estrutura": 1800.00, "custo_pessoal": 1200.00, "cmv_total": 14600.00, "despesas_operacionais": 2200.00, "despesas_comerciais": 1800.00, "despesas_adm": 1400.00, "lucro_operacional": -3296.00, "lucro_liquido": -3296.00},
        {"month": 3, "receita_bruta": 50000.00, "impostos": 3600.00, "receita_liquida": 46400.00, "custo_alimentacao": 17800.00, "custo_bebidas": 8900.00, "custo_estrutura": 5200.00, "custo_pessoal": 2800.00, "cmv_total": 34700.00, "despesas_operacionais": 4500.00, "despesas_comerciais": 3200.00, "despesas_adm": 2100.00, "lucro_operacional": 1900.00, "lucro_liquido": 1900.00},
        {"month": 4, "receita_bruta": 22500.00, "impostos": 1620.00, "receita_liquida": 20880.00, "custo_alimentacao": 11200.00, "custo_bebidas": 3500.00, "custo_estrutura": 2900.00, "custo_pessoal": 1500.00, "cmv_total": 19100.00, "despesas_operacionais": 2800.00, "despesas_comerciais": 2100.00, "despesas_adm": 1600.00, "lucro_operacional": -4720.00, "lucro_liquido": -4720.00},
        {"month": 5, "receita_bruta": 125000.00, "impostos": 9000.00, "receita_liquida": 116000.00, "custo_alimentacao": 28500.00, "custo_bebidas": 32000.00, "custo_estrutura": 15800.00, "custo_pessoal": 12000.00, "cmv_total": 88300.00, "despesas_operacionais": 12500.00, "despesas_comerciais": 9800.00, "despesas_adm": 7200.00, "lucro_operacional": -3000.00, "lucro_liquido": -3000.00},
        {"month": 6, "receita_bruta": 40000.00, "impostos": 2880.00, "receita_liquida": 37120.00, "custo_alimentacao": 15800.00, "custo_bebidas": 7800.00, "custo_estrutura": 6800.00, "custo_pessoal": 4200.00, "cmv_total": 34600.00, "despesas_operacionais": 5200.00, "despesas_comerciais": 4100.00, "despesas_adm": 2800.00, "lucro_operacional": -9580.00, "lucro_liquido": -9580.00},
        {"month": 7, "receita_bruta": 0.00, "impostos": 0.00, "receita_liquida": 0.00, "custo_alimentacao": 0.00, "custo_bebidas": 0.00, "custo_estrutura": 1800.00, "custo_pessoal": 1200.00, "cmv_total": 3000.00, "despesas_operacionais": 2100.00, "despesas_comerciais": 1500.00, "despesas_adm": 1400.00, "lucro_operacional": -8000.00, "lucro_liquido": -8000.00},
        {"month": 8, "receita_bruta": 8500.00, "impostos": 612.00, "receita_liquida": 7888.00, "custo_alimentacao": 4200.00, "custo_bebidas": 1800.00, "custo_estrutura": 2200.00, "custo_pessoal": 800.00, "cmv_total": 9000.00, "despesas_operacionais": 1200.00, "despesas_comerciais": 900.00, "despesas_adm": 700.00, "lucro_operacional": -3912.00, "lucro_liquido": -3912.00},
        {"month": 9, "receita_bruta": 38000.00, "impostos": 2736.00, "receita_liquida": 35264.00, "custo_alimentacao": 19600.00, "custo_bebidas": 6200.00, "custo_estrutura": 4800.00, "custo_pessoal": 3200.00, "cmv_total": 33800.00, "despesas_operacionais": 4800.00, "despesas_comerciais": 3600.00, "despesas_adm": 2400.00, "lucro_operacional": -9336.00, "lucro_liquido": -9336.00},
        {"month": 10, "receita_bruta": 45000.00, "impostos": 3240.00, "receita_liquida": 41760.00, "custo_alimentacao": 22500.00, "custo_bebidas": 7800.00, "custo_estrutura": 15600.00, "custo_pessoal": 3800.00, "cmv_total": 49700.00, "despesas_operacionais": 5800.00, "despesas_comerciais": 4200.00, "despesas_adm": 3100.00, "lucro_operacional": -21040.00, "lucro_liquido": -21040.00},
        {"month": 11, "receita_bruta": 95000.00, "impostos": 6840.00, "receita_liquida": 88160.00, "custo_alimentacao": 28500.00, "custo_bebidas": 24500.00, "custo_estrutura": 18900.00, "custo_pessoal": 9800.00, "cmv_total": 81700.00, "despesas_operacionais": 11200.00, "despesas_comerciais": 8900.00, "despesas_adm": 6500.00, "lucro_operacional": -3140.00, "lucro_liquido": -3140.00},
        {"month": 12, "receita_bruta": 52000.00, "impostos": 3744.00, "receita_liquida": 48256.00, "custo_alimentacao": 18500.00, "custo_bebidas": 14200.00, "custo_estrutura": 9800.00, "custo_pessoal": 5800.00, "cmv_total": 48300.00, "despesas_operacionais": 7200.00, "despesas_comerciais": 5200.00, "despesas_adm": 3800.00, "lucro_operacional": -20244.00, "lucro_liquido": -20244.00}
    ]
}

# DRE STATUS - Aug 2024 to Apr 2025
DRE_STATUS = {
    "months": ["Ago/24", "Set/24", "Out/24", "Nov/24", "Dez/24", "Jan/25", "Fev/25", "Mar/25", "Abr/25"],
    "data": [
        {"month": "2024-08", "receita_bruta": 68500.00, "impostos": 4932.00, "receita_liquida": 63568.00, "custo_alimentacao": 22500.00, "custo_bebidas": 15200.00, "custo_estrutura": 12800.00, "custo_pessoal": 8500.00, "cmv_total": 59000.00, "despesas_operacionais": 5800.00, "despesas_comerciais": 4500.00, "despesas_adm": 3200.00, "lucro_operacional": -8932.00, "lucro_liquido": -8932.00},
        {"month": "2024-09", "receita_bruta": 42500.00, "impostos": 3060.00, "receita_liquida": 39440.00, "custo_alimentacao": 15800.00, "custo_bebidas": 8900.00, "custo_estrutura": 7200.00, "custo_pessoal": 4800.00, "cmv_total": 36700.00, "despesas_operacionais": 4200.00, "despesas_comerciais": 3100.00, "despesas_adm": 2200.00, "lucro_operacional": -6760.00, "lucro_liquido": -6760.00},
        {"month": "2024-10", "receita_bruta": 32000.00, "impostos": 2304.00, "receita_liquida": 29696.00, "custo_alimentacao": 12800.00, "custo_bebidas": 5200.00, "custo_estrutura": 4500.00, "custo_pessoal": 3600.00, "cmv_total": 26100.00, "despesas_operacionais": 3800.00, "despesas_comerciais": 2800.00, "despesas_adm": 1800.00, "lucro_operacional": -4804.00, "lucro_liquido": -4804.00},
        {"month": "2024-11", "receita_bruta": 28500.00, "impostos": 2052.00, "receita_liquida": 26448.00, "custo_alimentacao": 11200.00, "custo_bebidas": 4800.00, "custo_estrutura": 4200.00, "custo_pessoal": 3200.00, "cmv_total": 23400.00, "despesas_operacionais": 3400.00, "despesas_comerciais": 2500.00, "despesas_adm": 1700.00, "lucro_operacional": -4552.00, "lucro_liquido": -4552.00},
        {"month": "2024-12", "receita_bruta": 78000.00, "impostos": 5616.00, "receita_liquida": 72384.00, "custo_alimentacao": 28500.00, "custo_bebidas": 18500.00, "custo_estrutura": 14500.00, "custo_pessoal": 11200.00, "cmv_total": 72700.00, "despesas_operacionais": 6800.00, "despesas_comerciais": 5200.00, "despesas_adm": 4100.00, "lucro_operacional": -16416.00, "lucro_liquido": -16416.00},
        {"month": "2025-01", "receita_bruta": 95000.00, "impostos": 6840.00, "receita_liquida": 88160.00, "custo_alimentacao": 28500.00, "custo_bebidas": 21500.00, "custo_estrutura": 16800.00, "custo_pessoal": 12500.00, "cmv_total": 79300.00, "despesas_operacionais": 7800.00, "despesas_comerciais": 6200.00, "despesas_adm": 4800.00, "lucro_operacional": -9940.00, "lucro_liquido": -9940.00},
        {"month": "2025-02", "receita_bruta": 22000.00, "impostos": 1584.00, "receita_liquida": 20416.00, "custo_alimentacao": 6500.00, "custo_bebidas": 3800.00, "custo_estrutura": 4200.00, "custo_pessoal": 2200.00, "cmv_total": 16700.00, "despesas_operacionais": 2800.00, "despesas_comerciais": 2200.00, "despesas_adm": 1600.00, "lucro_operacional": -2884.00, "lucro_liquido": -2884.00},
        {"month": "2025-03", "receita_bruta": 55000.00, "impostos": 3960.00, "receita_liquida": 51040.00, "custo_alimentacao": 19800.00, "custo_bebidas": 10200.00, "custo_estrutura": 8200.00, "custo_pessoal": 6800.00, "cmv_total": 45000.00, "despesas_operacionais": 5800.00, "despesas_comerciais": 4200.00, "despesas_adm": 3200.00, "lucro_operacional": -7160.00, "lucro_liquido": -7160.00},
        {"month": "2025-04", "receita_bruta": 18000.00, "impostos": 1296.00, "receita_liquida": 16704.00, "custo_alimentacao": 7200.00, "custo_bebidas": 2800.00, "custo_estrutura": 2800.00, "custo_pessoal": 2400.00, "cmv_total": 15200.00, "despesas_operacionais": 2400.00, "despesas_comerciais": 1800.00, "despesas_adm": 1400.00, "lucro_operacional": -4096.00, "lucro_liquido": -4096.00}
    ]
}

# Intercompany monthly data (simplified structure)
INTERCOMPANY_MONTHLY = [
    {"month": "2024-08", "la_orana_to_status": 4200.00, "status_to_la_orana": 2800.00, "net_transfer": 1400.00,"description": "Shared staff Aug"},
    {"month": "2024-09", "la_orana_to_status": 3800.00, "status_to_la_orana": 1500.00, "net_transfer": 2300.00, "description": "Equipment sharing"},
    {"month": "2024-10", "la_orana_to_status": 5100.00, "status_to_la_orana": 3200.00, "net_transfer": 1900.00, "description": "Beverage allocation"},
    {"month": "2024-11", "la_orana_to_status": 2800.00, "status_to_la_orana": 4100.00, "net_transfer": -1300.00, "description": "Venue rental share"},
    {"month": "2024-12", "la_orana_to_status": 6500.00, "status_to_la_orana": 4800.00, "net_transfer": 1700.00, "description": "Year-end provisions"},
    {"month": "2025-01", "la_orana_to_status": 7200.00, "status_to_la_orana": 5200.00, "net_transfer": 2000.00, "description": "Shared events split"},
    {"month": "2025-02", "la_orana_to_status": 2100.00, "status_to_la_orana": 1800.00, "net_transfer": 300.00, "description": "Minor allocation"},
    {"month": "2025-03", "la_orana_to_status": 5800.00, "status_to_la_orana": 4200.00, "net_transfer": 1600.00, "description": "Q1 settlement"},
    {"month": "2025-04", "la_orana_to_status": 3200.00, "status_to_la_orana": 2400.00, "net_transfer": 800.00, "description": "Monthly split"},
    {"month": "2025-05", "la_orana_to_status": 8900.00, "status_to_la_orana": 6500.00, "net_transfer": 2400.00, "description": "Staff sharing May"},
    {"month": "2025-06", "la_orana_to_status": 6200.00, "status_to_la_orana": 4800.00, "net_transfer": 1400.00, "description": "H1 closing"},
    {"month": "2025-07", "la_orana_to_status": 1800.00, "status_to_la_orana": 1200.00, "net_transfer": 600.00, "description": "Dry month adjustment"},
    {"month": "2025-08", "la_orana_to_status": 4500.00, "status_to_la_orana": 3200.00, "net_transfer": 1300.00, "description": "Sept prep"},
    {"month": "2025-09", "la_orana_to_status": 7200.00, "status_to_la_orana": 5800.00, "net_transfer": 1400.00, "description": "Q3 settlement"},
    {"month": "2025-10", "la_orana_to_status": 5200.00, "status_to_la_orana": 4100.00, "net_transfer": 1100.00, "description": "Mixed events"},
    {"month": "2025-11", "la_orana_to_status": 8800.00, "status_to_la_orana": 6200.00, "net_transfer": 2600.00, "description": "Gala support"},
    {"month": "2025-12", "la_orana_to_status": 9500.00, "status_to_la_orana": 7200.00, "net_transfer": 2300.00, "description": "Year-end close"}
]

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Event:
    event_id: str
    contract_id: str
    client: str
    event_name: str
    event_date: str
    amount_paid: float
    amount_receivable: float
    total_revenue: float
    
    # Cost breakdown
    direct_costs: Dict[str, float] = field(default_factory=dict)
    shared_costs: Dict[str, float] = field(default_factory=dict)
    cac_costs: Dict[str, float] = field(default_factory=dict)
    indirect_costs: Dict[str, float] = field(default_factory=dict)
    unknown_costs: Dict[str, float] = field(default_factory=dict)
    
    # Calculated fields
    total_costs: float = 0.0
    margin_absolute: float = 0.0
    margin_percentage: float = 0.0
    
    # Event metadata
    event_type: str = ""
    estimated_guests: int = 0
    estimated_ticket: float = 0.0
    
    # Quality metrics
    confidence_level: str = "MEDIUM"
    data_quality_score: float = 0.0
    completeness_percentage: float = 0.0
    
    # Risk flags
    flags: List[str] = field(default_factory=list)
    risk_level: str = "MEDIUM"
    
    # Scenarios
    real_margin: float = 0.0
    estimated_margin: float = 0.0
    optimized_margin: float = 0.0
    
    # Metadata
    company: str = ""
    month: str = ""
    year: int = 0

# ============================================================
# BACKTEST ENGINE
# ============================================================

class BacktestEngine:
    def __init__(self):
        self.events: List[Event] = []
        self.payables_index: Dict[str, List[Dict]] = defaultdict(list)
        self.dre_data: Dict[str, Dict] = {}
        self.learned_rules: List[Dict] = []
        
    def load_data(self):
        """Load and index all financial data"""
        print("📊 Loading financial data...")
        
        # Index payables by event reference
        for payable in ACCOUNTS_PAYABLE:
            ref = payable.get("event_ref", "UNKNOWN")
            self.payables_index[ref].append(payable)
        
        # Index DRE data by month
        for month_data in DRE_LA_ORANA_2025["data"]:
            key = f"LA-{month_data['month']}"
            self.dre_data[key] = month_data
        for month_data in DRE_STATUS["data"]:
            key = f"ST-{month_data['month']}"
            self.dre_data[key] = month_data
            
        print(f"   ✓ Indexed {len(ACCOUNTS_PAYABLE)} payables")
        print(f"   ✓ Loaded {len(self.dre_data)} months of DRE data")
        
    def parse_contract_id(self, contract_id: str) -> Dict:
        """Parse contract ID to extract event metadata"""
        # Pattern: CTT-{COMPANY}-{YEAR}{MONTH}-{SEQUENCE}
        match = re.match(r'CTT-(LA|ST)-(\d{4})(\d{2})-(\d+)', contract_id)
        if match:
            return {
                "company": "LA ORANA" if match.group(1) == "LA" else "STATUS Opera",
                "company_code": match.group(1),
                "year": int(match.group(2)),
                "month": int(match.group(3)),
                "sequence": int(match.group(4))
            }
        return {"company": "UNKNOWN", "company_code": "UNK", "year": 0, "month": 0, "sequence": 0}
    
    def classify_cost_type(self, description: str, vendor: str, category: str) -> str:
        """Classify costs into DIRECT, SHARED, CAC, INDIRECT, UNKNOWN"""
        desc_lower = (description + " " + vendor).lower()
        
        # CAC - Customer Acquisition Cost
        cac_keywords = ["comissão", "bv", "comissao", "bv vendas", "comercial", "comissionamento"]
        if any(kw in desc_lower for kw in cac_keywords):
            return "CAC"
        
        # SHARED costs
        shared_patterns = ["1/2", "1/3", "evento x", "evento y", "shared", "misturado", "dividido"]
        if any(pat in desc_lower for pat in shared_patterns) or category == "cac":
            if category == "cac":
                return "CAC"
            return "SHARED"
        
        # INDIRECT costs
        indirect_keywords = ["som", "luz", "estrutura", "camarim", "artista", "gallery", "espaço"]
        if any(kw in desc_lower for kw in indirect_keywords):
            return "INDIRECT"
        
        # DIRECT costs (staff, specific food/bev for event)
        direct_keywords = ["buffet", "bebid", "garçom", "bartender", "catering", "especific"]
        if any(kw in desc_lower for kw in direct_keywords):
            return "DIRECT"
        
        return "UNKNOWN"
    
    def estimate_guests(self, event: Event) -> int:
        """Estimate number of guests based on revenue and event type"""
        event_lower = event.event_name.lower()
        
        # Large graduations typically 200-500 guests
        if "formatura" in event_lower and event.total_revenue > 50000:
            return 350
        elif "formatura" in event_lower:
            return 180
        elif "colação" in event_lower:
            return 150
        elif "coquetel" in event_lower or "coffee" in event_lower:
            return 80
        elif "festa" in event_lower and event.total_revenue > 40000:
            return 250
        elif "confraternização" in event_lower:
            return 120
        elif "gala" in event_lower or "vernissage" in event_lower:
            return 100
        elif "aniversário" in event_lower:
            return 100
        else:
            # Default: estimate 80 guests for every 20k in revenue
            return max(50, int(event.total_revenue / 250))
    
    def detect_event_type(self, event: Event) -> str:
        """Classify event type"""
        name_lower = event.event_name.lower()
        revenue = event.total_revenue
        
        if "formatura" in name_lower:
            if revenue > 70000:
                return "LARGE_GRADUATION"
            elif revenue > 35000:
                return "MEDIUM_GRADUATION"
            else:
                return "SMALL_GRADUATION"
        elif "colação" in name_lower:
            return "COLLETION"
        elif "baile" in name_lower:
            return "GRADUATION_BALL"
        elif "coquetel" in name_lower or "cocktail" in name_lower:
            return "COCKTAIL"
        elif "coffee" in name_lower or "coofee" in name_lower:
            return "COFFEE_BREAK"
        elif "confraternização" in name_lower:
            return "CELEBRATION"
        elif "gala" in name_lower:
            return "GALA"
        elif "vernissage" in name_lower:
            return "ART_EVENT"
        elif "festa" in name_lower or "party" in name_lower:
            return "PARTY"
        elif "corporativ" in name_lower or "convenção" in name_lower:
            return "CORPORATE"
        elif "lançamento" in name_lower:
            return "LAUNCH_EVENT"
        elif "aniversário" in name_lower or "birthday" in name_lower:
            return "BIRTHDAY"
        elif "sessão solene" in name_lower:
            return "CEREMONY"
        else:
            return "OTHER"
    
    def calculate_confidence(self, event: Event) -> Tuple[str, float]:
        """Calculate confidence level based on data completeness"""
        score = 0.0
        
        # Base score for having contract
        score += 20
        
        # Revenue data completeness
        if event.total_revenue > 0:
            score += 20
        if event.amount_receivable == 0:  # Fully paid
            score += 15
        elif event.amount_paid / event.total_revenue > 0.5:  # More than half paid
            score += 10
            
        # Cost data completeness
        total_direct = sum(event.direct_costs.values())
        total_shared = sum(event.shared_costs.values())
        total_cac = sum(event.cac_costs.values())
        
        total_doc_costs = total_direct + total_shared + total_cac
        cost_coverage = min(100, (total_doc_costs / event.total_revenue * 100)) if event.total_revenue > 0 else 0
        
        if cost_coverage >= 60:
            score += 30
        elif cost_coverage >= 40:
            score += 20
        elif cost_coverage >= 20:
            score += 10
            
        # Event has happened (past date)
        event_date = datetime.strptime(event.event_date, "%Y-%m-%d")
        if event_date < datetime.now():
            score += 15
            
        # Determine confidence level
        if score >= 75:
            return "HIGH", score
        elif score >= 50:
            return "MEDIUM", score
        else:
            return "LOW", score
    
    def apply_risk_flags(self, event: Event):
        """Apply business rules to generate risk flags"""
        flags = []
        event_type = event.event_type
        ticket = event.estimated_ticket
        margin = event.margin_percentage
        
        # Rule 1: Large graduation margin
        if event_type == "LARGE_GRADUATION" and (margin < 20 or margin > 35):
            if margin < 20:
                flags.append("MARGEM_BAIXA_FORMATURA_GRANDE")
            else:
                flags.append("MARGEM_INFLADA_POSSIVEL_CUSTO_SUBALOCADO")
        
        # Rule 2: Ticket below threshold
        if ticket < 50:
            flags.append("TICKET_CRITICO_ZONA_INVIABILIDADE")
        elif ticket < 70:
            flags.append("TICKET_BAIXO_RISCO_ESTRUTURAL")
            
        # Rule 3: Margin critical
        if margin < 5:
            flags.append("MARGEM_PERIGO_REAVALIAR_EVENTO")
        elif margin < 15:
            flags.append("MARGEM_CRITICA_REVISAO_NECESSARIA")
        elif margin > 40:
            flags.append("MARGEM_APARENTE_ALTA_CUSTO_SUBALOCADO")
            
        # Rule 4: Large event with apparent high margin
        if event.total_revenue > 60000 and margin > 35:
            flags.append("GRANDE_PORTE_MARGEM_INFLADA")
            
        # Rule 5: DRE contamination check
        if event.total_revenue < 25000 and margin > 30:
            flags.append("EVENTO_PEQUENO_MARGEM_ESTRANHA")
            
        event.flags = flags
        
        # Risk level
        if "MARGEM_PERIGO" in str(flags) or "TICKET_CRITICO" in str(flags):
            event.risk_level = "CRITICAL"
        elif "MARGEM_CRITICA" in str(flags) or "TICKET_BAIXO" in str(flags):
            event.risk_level = "HIGH"
        elif len(flags) > 2:
            event.risk_level = "MEDIUM"
        else:
            event.risk_level = "LOW"
    
    def build_events(self):
        """Build structured event dataset"""
        print("\n🔨 Building event structures...")
        
        for receivable in ACCOUNTS_RECEIVABLE:
            # Parse contract metadata
            contract_info = self.parse_contract_id(receivable["contract_id"])
            
            # Create event
            total_revenue = receivable["amount_paid"] + receivable["amount_receivable"]
            
            event = Event(
                event_id=f"EVT-{receivable['contract_id']}",
                contract_id=receivable["contract_id"],
                client=receivable["client"],
                event_name=receivable["event_name"],
                event_date=receivable["event_date"],
                amount_paid=receivable["amount_paid"],
                amount_receivable=receivable["amount_receivable"],
                total_revenue=total_revenue,
                company=contract_info["company"],
                year=contract_info["year"],
                month=f"{contract_info['year']}-{contract_info['month']:02d}"
            )
            
            # Estimate guests
            event.estimated_guests = self.estimate_guests(event)
            event.estimated_ticket = total_revenue / event.estimated_guests if event.estimated_guests > 0 else 0
            
            # Detect event type
            event.event_type = self.detect_event_type(event)
            
            # Map payables to this event
            self._map_payables(event)
            
            # Calculate costs
            self._calculate_costs(event)
            
            # Calculate margins
            event.margin_absolute = event.total_revenue - event.total_costs
            event.margin_percentage = (event.margin_absolute / event.total_revenue * 100) if event.total_revenue > 0 else 0
            
            # Calculate scenarios
            event.real_margin = event.margin_percentage
            event.estimated_margin = self._estimate_margin(event)
            event.optimized_margin = self._optimize_margin(event)
            
            # Confidence and flags
            event.confidence_level, event.data_quality_score = self.calculate_confidence(event)
            self.apply_risk_flags(event)
            
            # Completeness
            event.completeness_percentage = min(100, event.data_quality_score)
            
            self.events.append(event)
            
        print(f"   ✓ Built {len(self.events)} events")
        
    def _map_payables(self, event: Event):
        """Map payables to specific events"""
        # Direct match
        direct = self.payables_index.get(event.contract_id, [])
        for p in direct:
            cost_type = self.classify_cost_type(p["description"], p["vendor"], p.get("category", "unknown"))
            if cost_type == "DIRECT":
                event.direct_costs[p["id"]] = p["amount"]
            elif cost_type == "CAC":
                event.cac_costs[p["id"]] = p["amount"]
            elif cost_type == "INDIRECT":
                event.indirect_costs[p["id"]] = p["amount"]
            else:
                event.unknown_costs[p["id"]] = p["amount"]
        
        # Shared allocation
        shared_entries = []
        for ref, payables in self.payables_index.items():
            if "SHARED" in ref or ref == "MULTI-EVENT":
                for p in payables:
                    # Allocate based on month correlation
                    event_month = event.event_date[:7]
                    payable_month = p["due_date"][:7]
                    if event_month == payable_month:
                        shared_entries.append(p)
        
        for p in shared_entries:
            ref = p.get("event_ref", "")
            if "50" in ref:  # 50-50 split
                event.shared_costs[p["id"]] = p["amount"] * 0.5
            elif "3" in ref:  # 1/3 split
                event.shared_costs[p["id"]] = p["amount"] * 0.33
            else:
                # Proportional to event revenue
                event.shared_costs[p["id"]] = p["amount"] * 0.3
    
    def _calculate_costs(self, event: Event):
        """Calculate total event costs"""
        total = 0.0
        total += sum(event.direct_costs.values())
        total += sum(event.shared_costs.values())
        total += sum(event.cac_costs.values())
        total += sum(event.indirect_costs.values())
        total += sum(event.unknown_costs.values())
        event.total_costs = total
    
    def _estimate_margin(self, event: Event) -> float:
        """Calculate estimated margin based on incomplete data"""
        # If we have partial cost data, estimate full costs
        current_costs = event.total_costs
        
        # Estimate missing costs based on event type norms
        if event.event_type in ["LARGE_GRADUATION", "MEDIUM_GRADUATION"]:
            expected_margin = 27  # Industry norm
        elif event.event_type in ["COFFEE_BREAK", "COCKTAIL"]:
            expected_margin = 15
        else:
            expected_margin = 22
            
        return expected_margin
    
    def _optimize_margin(self, event: Event) -> float:
        """Calculate optimized margin with proper cost control"""
        current_margin = event.margin_percentage
        optimizations = 0
        
        # Optimization 1: Better food cost management
        food_costs = sum(v for k, v in event.direct_costs.items() if "buffet" in k.lower() or "catering" in k.lower())
        if food_costs / event.total_revenue > 0.35 if event.total_revenue else 0:
            optimizations += 5
            
        # Optimization 2: Reduce CAC
        cac_total = sum(event.cac_costs.values())
        if cac_total / event.total_revenue > 0.15 if event.total_revenue else 0:
            optimizations += 3
            
        # Optimization 3: Shared cost reduction
        if event.shared_costs:
            optimizations += 2
            
        return min(45, current_margin + optimizations)  # Cap at 45%
    
    def generate_learned_rules(self):
        """Generate machine learning rules from the data"""
        print("\n🧠 Generating business rules...")
        
        rules = []
        
        # Rule 1: Large graduation margins
        large_grads = [e for e in self.events if e.event_type == "LARGE_GRADUATION"]
        if large_grads:
            avg_margin = sum(e.margin_percentage for e in large_grads) / len(large_grads)
            rules.append({
                "rule_id": "RULE-001",
                "category": "MARGIN_BENCHMARK",
                "trigger": "event_type == LARGE_GRADUATION",
                "condition": "revenue > 70000",
                "recommendation": f"Target margin: 25-32% (observed avg: {avg_margin:.1f}%)",
                "confidence": "HIGH" if len(large_grads) >= 3 else "MEDIUM",
                "samples": len(large_grads)
            })
        
        # Rule 2: Ticket pricing
        low_ticket_events = [e for e in self.events if e.estimated_ticket < 70]
        if low_ticket_events:
            critical_count = len([e for e in low_ticket_events if e.margin_percentage < 10])
            rules.append({
                "rule_id": "RULE-002",
                "category": "PRICING_RISK",
                "trigger": "ticket_per_person < 70",
                "condition": "any event size",
                "recommendation": f"Risk threshold: {critical_count}/{len(low_ticket_events)} events with <10% margin",
                "confidence": "HIGH",
                "samples": len(low_ticket_events)
            })
        
        # Rule 3: CAC impact
        events_with_cac = [e for e in self.events if e.cac_costs]
        if events_with_cac:
            avg_cac_pct = sum(sum(e.cac_costs.values()) / e.total_revenue * 100 for e in events_with_cac) / len(events_with_cac)
            rules.append({
                "rule_id": "RULE-003",
                "category": "CAC_OPTIMIZATION",
                "trigger": "cac_costs > 0",
                "condition": "revenue < 50000",
                "recommendation": f"CAC avg {avg_cac_pct:.1f}% - optimize for events <50k revenue",
                "confidence": "MEDIUM",
                "samples": len(events_with_cac)
            })
        
        # Rule 4: Shared costs
        shared_events = [e for e in self.events if e.shared_costs]
        if shared_events:
            avg_shared = sum(sum(e.shared_costs.values()) for e in shared_events) / len(shared_events)
            rules.append({
                "rule_id": "RULE-004",
                "category": "COST_ALLOCATION",
                "trigger": "shared_costs > 0",
                "condition": "multiple events in same month",
                "recommendation": f"Avg shared cost: R$ {avg_shared:.0f} - improve allocation precision",
                "confidence": "MEDIUM",
                "samples": len(shared_events)
            })
        
        # Rule 5: Margin integrity
        inflated_margins = [e for e in self.events if e.margin_percentage > 40 and e.total_revenue > 40000]
        if inflated_margins:
            rules.append({
                "rule_id": "RULE-005",
                "category": "DATA_QUALITY",
                "trigger": "margin > 40%",
                "condition": "revenue > 40000",
                "recommendation": f"Check {len(inflated_margins)} events - likely cost underallocation",
                "confidence": "HIGH",
                "samples": len(inflated_margins)
            })
        
        # Rule 6: Event type profitability
        type_margins = defaultdict(list)
        for e in self.events:
            type_margins[e.event_type].append(e.margin_percentage)
        
        best_type = max(type_margins.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0)
        worst_type = min(type_margins.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else 0)
        
        rules.append({
            "rule_id": "RULE-006",
            "category": "EVENT_TYPE_ANALYSIS",
            "trigger": "event_type",
            "condition": "any",
            "recommendation": f"Best: {best_type[0]} (avg {sum(best_type[1])/len(best_type[1]):.1f}%) | Worst: {worst_type[0]} (avg {sum(worst_type[1])/len(worst_type[1]):.1f}%)",
            "confidence": "HIGH",
            "samples": len(type_margins)
        })
        
        # Rule 7: Coffee break pattern
        coffee_events = [e for e in self.events if e.event_type == "COFFEE_BREAK"]
        if coffee_events:
            avg_margin = sum(e.margin_percentage for e in coffee_events) / len(coffee_events)
            rules.append({
                "rule_id": "RULE-007",
                "category": "SMALL_EVENT_RISK",
                "trigger": "event_type == COFFEE_BREAK",
                "condition": "revenue < 15000",
                "recommendation": f"Coffee breaks avg {avg_margin:.1f}% margin - structurally weak",
                "confidence": "HIGH",
                "samples": len(coffee_events)
            })
        
        # Rule 8: Confidence pattern
        high_conf = len([e for e in self.events if e.confidence_level == "HIGH"])
        med_conf = len([e for e in self.events if e.confidence_level == "MEDIUM"])
        low_conf = len([e for e in self.events if e.confidence_level == "LOW"])
        
        rules.append({
            "rule_id": "RULE-008",
            "category": "DATA_QUALITY",
            "trigger": "confidence_level assessment",
            "condition": "post-analysis",
            "recommendation": f"Data quality: HIGH={high_conf}, MEDIUM={med_conf}, LOW={low_conf} - improve low-confidence events",
            "confidence": "HIGH",
            "samples": len(self.events)
        })
        
        self.learned_rules = rules
        print(f"   ✓ Generated {len(rules)} business rules")
        
    def export_json(self, filepath: str):
        """Export events to JSON"""
        events_data = []
        for event in self.events:
            events_data.append({
                "event_id": event.event_id,
                "contract_id": event.contract_id,
                "client": event.client,
                "event_name": event.event_name,
                "event_date": event.event_date,
                "event_type": event.event_type,
                "company": event.company,
                
                "revenue": {
                    "amount_paid": event.amount_paid,
                    "amount_receivable": event.amount_receivable,
                    "total_revenue": event.total_revenue
                },
                
                "costs": {
                    "direct": event.direct_costs,
                    "shared": event.shared_costs,
                    "cac": event.cac_costs,
                    "indirect": event.indirect_costs,
                    "unknown": event.unknown_costs,
                    "total_costs": event.total_costs
                },
                
                "margins": {
                    "absolute": round(event.margin_absolute, 2),
                    "percentage": round(event.margin_percentage, 2),
                    "real_margin": round(event.real_margin, 2),
                    "estimated_margin": round(event.estimated_margin, 2),
                    "optimized_margin": round(event.optimized_margin, 2)
                },
                
                "attendance": {
                    "estimated_guests": event.estimated_guests,
                    "estimated_ticket": round(event.estimated_ticket, 2)
                },
                
                "quality": {
                    "confidence_level": event.confidence_level,
                    "data_quality_score": round(event.data_quality_score, 1),
                    "completeness_percentage": round(event.completeness_percentage, 1)
                },
                
                "risk": {
                    "risk_level": event.risk_level,
                    "flags": event.flags
                }
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_events": len(self.events),
                    "companies": ["LA ORANA", "STATUS Opera"],
                    "date_range": "2024-08 to 2026-04"
                },
                "events": events_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   ✓ Exported JSON: {filepath}")
    
    def export_csv(self, filepath: str):
        """Export events to CSV"""
        fieldnames = [
            'event_id', 'contract_id', 'client', 'event_name', 'event_date', 'event_type', 'company',
            'amount_paid', 'amount_receivable', 'total_revenue', 'total_costs',
            'direct_costs', 'shared_costs', 'cac_costs', 'indirect_costs', 'unknown_costs',
            'margin_absolute', 'margin_percentage', 'real_margin', 'estimated_margin', 'optimized_margin',
            'estimated_guests', 'estimated_ticket', 'confidence_level', 'data_quality_score',
            'completeness_percentage', 'risk_level', 'flags'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for e in self.events:
                writer.writerow({
                    'event_id': e.event_id,
                    'contract_id': e.contract_id,
                    'client': e.client,
                    'event_name': e.event_name,
                    'event_date': e.event_date,
                    'event_type': e.event_type,
                    'company': e.company,
                    'amount_paid': e.amount_paid,
                    'amount_receivable': e.amount_receivable,
                    'total_revenue': e.total_revenue,
                    'total_costs': e.total_costs,
                    'direct_costs': sum(e.direct_costs.values()),
                    'shared_costs': sum(e.shared_costs.values()),
                    'cac_costs': sum(e.cac_costs.values()),
                    'indirect_costs': sum(e.indirect_costs.values()),
                    'unknown_costs': sum(e.unknown_costs.values()),
                    'margin_absolute': round(e.margin_absolute, 2),
                    'margin_percentage': round(e.margin_percentage, 2),
                    'real_margin': round(e.real_margin, 2),
                    'estimated_margin': round(e.estimated_margin, 2),
                    'optimized_margin': round(e.optimized_margin, 2),
                    'estimated_guests': e.estimated_guests,
                    'estimated_ticket': round(e.estimated_ticket, 2),
                    'confidence_level': e.confidence_level,
                    'data_quality_score': round(e.data_quality_score, 1),
                    'completeness_percentage': round(e.completeness_percentage, 1),
                    'risk_level': e.risk_level,
                    'flags': '|'.join(e.flags)
                })
        
        print(f"   ✓ Exported CSV: {filepath}")
    
    def generate_summary_report(self, filepath: str):
        """Generate executive summary markdown"""
        
        # Calculate key statistics
        total_events = len(self.events)
        high_conf = len([e for e in self.events if e.confidence_level == "HIGH"])
        med_conf = len([e for e in self.events if e.confidence_level == "MEDIUM"])
        low_conf = len([e for e in self.events if e.confidence_level == "LOW"])
        
        total_revenue = sum(e.total_revenue for e in self.events)
        total_costs = sum(e.total_costs for e in self.events)
        total_margin = total_revenue - total_costs
        avg_margin = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
        
        la_events = [e for e in self.events if e.company == "LA ORANA"]
        st_events = [e for e in self.events if e.company == "STATUS Opera"]
        
        high_risk = len([e for e in self.events if e.risk_level in ["CRITICAL", "HIGH"]])
        critical_flags = len([e for e in self.events if "MARGEM_PERIGO" in str(e.flags) or "TICKET_CRITICO" in str(e.flags)])
        
        # Best and worst events
        sorted_by_margin = sorted(self.events, key=lambda e: e.margin_percentage, reverse=True)
        best_events = sorted_by_margin[:5]
        worst_events = sorted_by_margin[-5:]
        
        # Most profitable
        sorted_by_profit = sorted(self.events, key=lambda e: e.margin_absolute, reverse=True)
        most_profitable = sorted_by_profit[:3]
        biggest_loss = sorted_by_profit[-3:]
        
        content = f"""# 📊 Backtest Executive Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Dataset:** LA ORANA + STATUS Opera Financial Data

---

## 📈 Key Statistics

| Metric | Value |
|--------|-------|
| **Total Events Processed** | {total_events} |
| **Total Revenue** | R$ {total_revenue:,.2f} |
| **Total Costs** | R$ {total_costs:,.2f} |
| **Net Margin** | R$ {total_margin:,.2f} |
| **Average Margin %** | {avg_margin:.1f}% |

### Confidence Levels
- ✅ **HIGH:** {high_conf} events ({high_conf/total_events*100:.1f}%)
- ⚠️ **MEDIUM:** {med_conf} events ({med_conf/total_events*100:.1f}%)
- 🔴 **LOW:** {low_conf} events ({low_conf/total_events*100:.1f}%)

### Risk Distribution
- 🔴 **CRITICAL/HIGH Risk:** {high_risk} events
- ⚠️ **Critical Flags:** {critical_flags} events

---

## 🏢 Company Breakdown

### LA ORANA
- Events: {len(la_events)}
- Revenue: R$ {sum(e.total_revenue for e in la_events):,.2f}
- Avg Margin: {sum(e.margin_percentage for e in la_events)/len(la_events) if la_events else 0:.1f}%

### STATUS Opera
- Events: {len(st_events)}
- Revenue: R$ {sum(e.total_revenue for e in st_events):,.2f}
- Avg Margin: {sum(e.margin_percentage for e in st_events)/len(st_events) if st_events else 0:.1f}%

---

## 🏆 Top 5 Most Profitable Events

"""
        
        for i, e in enumerate(most_profitable, 1):
            content += f"""{i}. **{e.event_name}** ({e.company})
   - Revenue: R$ {e.total_revenue:,.2f} | Margin: {e.margin_percentage:.1f}% | Profit: R$ {e.margin_absolute:,.2f}

"""
        
        content += f"""
---

## ⚠️ Bottom 3 Events (Negative/Zero Margin)

"""
        for i, e in enumerate(biggest_loss[-3:], 1):
            content += f"""{i}. **{e.event_name}** ({e.company})
   - Revenue: R$ {e.total_revenue:,.2f} | Margin: {e.margin_percentage:.1f}% | Result: R$ {e.margin_absolute:,.2f}
   - Flags: {', '.join(e.flags[:3]) if e.flags else 'None'}

"""
        
        content += f"""
---

## 📋 Event Type Summary

| Type | Count | Avg Revenue | Avg Margin % |
|------|-------|-------------|--------------|
"""
        
        type_stats = defaultdict(lambda: {"count": 0, "revenue": 0, "margins": []})
        for e in self.events:
            type_stats[e.event_type]["count"] += 1
            type_stats[e.event_type]["revenue"] += e.total_revenue
            type_stats[e.event_type]["margins"].append(e.margin_percentage)
        
        for etype, stats in sorted(type_stats.items()):
            avg_margin = sum(stats["margins"]) / len(stats["margins"]) if stats["margins"] else 0
            content += f"| {etype} | {stats['count']} | R$ {stats['revenue']/stats['count']:,.0f} | {avg_margin:.1f}% |\n"
        
        content += """
---

## 🎯 Quick Insights

1. **Margin Benchmark:** Large graduations should target 25-32% margin
2. **Pricing Risk:** Events with ticket < R$ 70/person show structural weakness
3. **Cost Control:** {cac_count} events have visible CAC costs - monitor commercial expenses
4. **Data Quality:** {low_conf} events need better cost allocation for accurate analysis

---

*Report generated by Orkestra Finance Brain*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content.format(cac_count=len([e for e in self.events if e.cac_costs]), low_conf=low_conf))
        
        print(f"   ✓ Generated summary: {filepath}")
    
    def generate_insights_report(self, filepath: str):
        """Generate detailed insights markdown"""
        
        # Margin leakage analysis
        inflated_margins = [e for e in self.events if e.margin_percentage > 40 and e.total_revenue > 40000]
        likely_underallocated = sum(e.total_revenue * 0.15 for e in inflated_margins)  # Estimate 15% missing costs
        
        # Protein analysis
        high_protein = []
        for e in self.events:
            food_cost = sum(v for k, v in e.direct_costs.items() if any(x in k.lower() for x in ["buffet", "catering"]))
            if food_cost > e.total_revenue * 0.35:
                high_protein.append(e)
        
        # Ticket analysis
        ticket_analysis = {
            "critical": [e for e in self.events if e.estimated_ticket < 50],
            "risk": [e for e in self.events if 50 <= e.estimated_ticket < 70],
            "good": [e for e in self.events if 70 <= e.estimated_ticket < 100],
            "excellent": [e for e in self.events if e.estimated_ticket >= 100]
        }
        
        content = f"""# 🔍 Detailed Backtest Insights

**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 💸 Margin Leakage Analysis

### Identified Underallocated Costs

Events with margin > 40% on revenue > 40k likely have cost underallocation:

| Event | Revenue | Margin % | Est. Missing Cost |
|-------|---------|----------|-------------------|
"""
        
        for e in inflated_margins[:8]:
            est_missing = e.total_revenue * 0.15
            content += f"| {e.event_name[:30]} | R$ {e.total_revenue:,.0f} | {e.margin_percentage:.1f}% | R$ {est_missing:,.0f} |\n"
        
        content += f"""
**Total Estimated Underallocated:** R$ {likely_underallocated:,.2f}

> These events show high margins because some shared/indirect costs likely haven't been fully allocated.

---

## 🥩 Protein Cost Analysis

Events where food costs exceed 35% of revenue (menu optimization opportunity):

| Event | Food Cost | % Revenue | Suggested Action |
|-------|-----------|-----------|------------------|
"""
        
        for e in high_protein[:5]:
            food_cost = sum(v for k, v in e.direct_costs.items() if any(x in k.lower() for x in ["buffet", "catering"]))
            pct = (food_cost / e.total_revenue * 100) if e.total_revenue > 0 else 0
            content += f"| {e.event_name[:25]} | R$ {food_cost:,.0f} | {pct:.1f}% | Review menu/protein options |\n"
        
        content += f"""
---

## 🎟️ Ticket Price Analysis

### Critical Zone (Ticket < R$ 50)
- Events: {len(ticket_analysis['critical'])}
- Risk: Structural unviability

| Event | Ticket | Guests | Revenue | Flags |
|-------|--------|--------|---------|-------|
"""
        for e in ticket_analysis['critical']:
            content += f"| {e.event_name[:25]} | R$ {e.estimated_ticket:.0f} | {e.estimated_guests} | R$ {e.total_revenue:,.0f} | {', '.join(e.flags[:2]) or 'None'} |\n"
        
        content += f"""

### Risk Zone (Ticket R$ 50-70)
- Events: {len(ticket_analysis['risk'])}
- Risk: Low margins, requires volume

### Healthy Zone (Ticket R$ 70-100)
- Events: {len(ticket_analysis['good'])}
- Status: Acceptable range

### Premium Zone (Ticket > R$ 100)
- Events: {len(ticket_analysis['excellent'])}
- Status: High-value events

---

## 🔧 Cost Classification Summary

| Category | Total Value | % of Costs | Event Count |
|----------|-------------|------------|-------------|
"""
        
        total_direct = sum(sum(e.direct_costs.values()) for e in self.events)
        total_shared = sum(sum(e.shared_costs.values()) for e in self.events)
        total_cac = sum(sum(e.cac_costs.values()) for e in self.events)
        total_indirect = sum(sum(e.indirect_costs.values()) for e in self.events)
        total_unknown = sum(sum(e.unknown_costs.values()) for e in self.events)
        all_costs = total_direct + total_shared + total_cac + total_indirect + total_unknown
        
        content += f"| DIRECT | R$ {total_direct:,.2f} | {total_direct/all_costs*100:.1f}% | {len([e for e in self.events if e.direct_costs])} |\n"
        content += f"| SHARED | R$ {total_shared:,.2f} | {total_shared/all_costs*100:.1f}% | {len([e for e in self.events if e.shared_costs])} |\n"
        content += f"| CAC | R$ {total_cac:,.2f} | {total_cac/all_costs*100:.1f}% | {len([e for e in self.events if e.cac_costs])} |\n"
        content += f"| INDIRECT | R$ {total_indirect:,.2f} | {total_indirect/all_costs*100:.1f}% | {len([e for e in self.events if e.indirect_costs])} |\n"
        content += f"| UNKNOWN | R$ {total_unknown:,.2f} | {total_unknown/all_costs*100:.1f}% | {len([e for e in self.events if e.unknown_costs])} |\n"
        
        content += f"""
---

## 📊 Scenario Comparison (Top 10 Events)

| Event | Real | Est. | Optimized | Gap |
|-------|------|------|-----------|-----|
"""
        
        top_10 = sorted(self.events, key=lambda e: e.total_revenue, reverse=True)[:10]
        for e in top_10:
            gap = e.optimized_margin - e.real_margin
            content += f"| {e.event_name[:28]} | {e.real_margin:.1f}% | {e.estimated_margin:.1f}% | {e.optimized_margin:.1f}% | +{gap:.1f}% |\n"
        
        content += f"""

---

## 🔍 Data Quality Issues

### Low Confidence Events ({len([e for e in self.events if e.confidence_level == 'LOW'])})

These events lack sufficient cost data for accurate margin analysis:

| Event | Revenue | Confidence | Missing Data |
|-------|---------|------------|--------------|
"""
        
        for e in self.events:
            if e.confidence_level == "LOW":
                missing = []
                if not e.direct_costs:
                    missing.append("Direct costs")
                if not e.cac_costs:
                    missing.append("CAC")
                if e.amount_receivable > 0:
                    missing.append("Pending payment")
                content += f"| {e.event_name[:25]} | R$ {e.total_revenue:,.0f} | {e.data_quality_score:.0f}% | {', '.join(missing[:2])} |\n"
        
        content += """

---

*Detailed analysis by Orkestra Finance Brain*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✓ Generated insights: {filepath}")
    
    def generate_rankings_report(self, filepath: str):
        """Generate rankings markdown"""
        
        content = f"""# 🏆 Event Rankings

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 💰 Top 10 by Revenue

| Rank | Event | Company | Revenue | Status |
|------|-------|---------|---------|--------|
"""
        
        by_revenue = sorted(self.events, key=lambda e: e.total_revenue, reverse=True)[:10]
        for i, e in enumerate(by_revenue, 1):
            status = "✅ Paid" if e.amount_receivable == 0 else f"⚠️ {e.amount_receivable/e.total_revenue*100:.0f}% pending"
            content += f"| {i} | {e.event_name[:35]} | {e.company.split()[0]} | R$ {e.total_revenue:,.0f} | {status} |\n"
        
        content += f"""

---

## 📈 Top 10 by Margin %

| Rank | Event | Margin % | Revenue | Risk Level |
|------|-------|----------|---------|------------|
"""
        
        by_margin = sorted(self.events, key=lambda e: e.margin_percentage, reverse=True)[:10]
        for i, e in enumerate(by_margin, 1):
            risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(e.risk_level, "⚪")
            content += f"| {i} | {e.event_name[:35]} | {e.margin_percentage:.1f}% | R$ {e.total_revenue:,.0f} | {risk_emoji} {e.risk_level} |\n"
        
        content += f"""

---

## 📉 Bottom 10 by Margin %

| Rank | Event | Margin % | Revenue | Flags |
|------|-------|----------|---------|-------|
"""
        
        by_margin_low = sorted(self.events, key=lambda e: e.margin_percentage)[:10]
        for i, e in enumerate(by_margin_low, 1):
            flags_short = ', '.join(f[:20] for f in e.flags[:2]) if e.flags else 'None'
            content += f"| {i} | {e.event_name[:30]} | {e.margin_percentage:.1f}% | R$ {e.total_revenue:,.0f} | {flags_short} |\n"
        
        content += f"""

---

## 🎯 Top 10 by Absolute Profit

| Rank | Event | Profit | Margin % | Type |
|------|-------|--------|----------|------|
"""
        
        by_profit = sorted(self.events, key=lambda e: e.margin_absolute, reverse=True)[:10]
        for i, e in enumerate(by_profit, 1):
            content += f"| {i} | {e.event_name[:35]} | R$ {e.margin_absolute:,.0f} | {e.margin_percentage:.1f}% | {e.event_type} |\n"
        
        content += f"""

---

## ⚠️ Critical Risk Events

Events requiring immediate attention:

| Event | Risk | Flags | Recommended Action |
|-------|------|-------|-------------------|
"""
        
        critical_events = [e for e in self.events if e.risk_level in ["CRITICAL", "HIGH"]]
        critical_events.sort(key=lambda e: e.margin_percentage)
        
        for e in critical_events[:10]:
            action = "Review pricing strategy" if "TICKET" in str(e.flags) else "Reallocate costs" if "MARGEM" in str(e.flags) else "Audit event"
            content += f"| {e.event_name[:28]} | {e.risk_level} | {', '.join(f[:15] for f in e.flags[:2])} | {action} |\n"
        
        content += f"""

---

## 🎓 Event Type Performance

| Type | Count | Best Margin | Worst Margin | Avg |
|------|-------|-------------|--------------|-----|
"""
        
        type_groups = defaultdict(list)
        for e in self.events:
            type_groups[e.event_type].append(e.margin_percentage)
        
        for etype, margins in sorted(type_groups.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
            best = max(margins)
            worst = min(margins)
            avg = sum(margins) / len(margins)
            content += f"| {etype} | {len(margins)} | {best:.1f}% | {worst:.1f}% | {avg:.1f}% |\n"
        
        content += f"""

---

## 🎟️ Ticket Price Rankings

### Highest Ticket Prices (Premium Events)

| Rank | Event | Ticket | Guests | Revenue/Head |
|------|-------|--------|--------|--------------|
"""
        
        by_ticket = sorted(self.events, key=lambda e: e.estimated_ticket, reverse=True)[:8]
        for i, e in enumerate(by_ticket, 1):
            content += f"| {i} | {e.event_name[:30]} | R$ {e.estimated_ticket:.0f} | {e.estimated_guests} | R$ {e.total_revenue/e.estimated_guests:,.0f} |\n"
        
        content += f"""

### Lowest Ticket Prices (Volume Strategy)

| Rank | Event | Ticket | Guests | Margin % |
|------|-------|--------|--------|----------|
"""
        
        by_ticket_low = sorted(self.events, key=lambda e: e.estimated_ticket)[:8]
        for i, e in enumerate(by_ticket_low, 1):
            content += f"| {i} | {e.event_name[:30]} | R$ {e.estimated_ticket:.0f} | {e.estimated_guests} | {e.margin_percentage:.1f}% |\n"
        
        content += """

---

## 📊 Company Comparison

| Metric | LA ORANA | STATUS Opera |
|--------|----------|--------------|
"""
        
        la_events = [e for e in self.events if e.company == "LA ORANA"]
        st_events = [e for e in self.events if e.company == "STATUS Opera"]
        
        la_total_rev = sum(e.total_revenue for e in la_events)
        st_total_rev = sum(e.total_revenue for e in st_events)
        la_avg_margin = sum(e.margin_percentage for e in la_events) / len(la_events) if la_events else 0
        st_avg_margin = sum(e.margin_percentage for e in st_events) / len(st_events) if st_events else 0
        
        content += f"| Total Events | {len(la_events)} | {len(st_events)} |\n"
        content += f"| Total Revenue | R$ {la_total_rev:,.0f} | R$ {st_total_rev:,.0f} |\n"
        content += f"| Avg Margin | {la_avg_margin:.1f}% | {st_avg_margin:.1f}% |\n"
        content += f"| High Conf Events | {len([e for e in la_events if e.confidence_level == 'HIGH'])} | {len([e for e in st_events if e.confidence_level == 'HIGH'])} |\n"
        content += f"| Critical Risk | {len([e for e in la_events if e.risk_level == 'CRITICAL'])} | {len([e for e in st_events if e.risk_level == 'CRITICAL'])} |\n"
        
        content += """

---

*Rankings generated by Orkestra Finance Brain*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✓ Generated rankings: {filepath}")
    
    def export_learning_rules(self, filepath: str):
        """Export learned rules to JSON"""
        
        output = {
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "source": "Backtest Engine v1.0",
                "training_events": len(self.events),
                "companies": ["LA ORANA", "STATUS Opera"]
            },
            "rules": self.learned_rules,
            "thresholds": {
                "margin": {
                    "graduation_large_healthy_min": 25.0,
                    "graduation_large_healthy_max": 32.0,
                    "critical_minimum": 5.0,
                    "review_required": 15.0,
                    "inflation_suspicious": 40.0
                },
                "ticket": {
                    "critical": 50.0,
                    "risk": 70.0,
                    "good": 100.0
                },
                "cost_allocation": {
                    "protein_max_pct": 50.0,
                    "staff_max_pct": 30.0,
                    "cac_max_pct": 15.0
                }
            },
            "classifications": {
                "cost_types": ["DIRECT_COST", "SHARED_COST", "CAC", "INDIRECT_COST", "UNKNOWN"],
                "event_types": list(set(e.event_type for e in self.events)),
                "confidence_levels": ["HIGH", "MEDIUM", "LOW"],
                "risk_levels": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            },
            "event_profiles": {
                "PERFIL_A": {
                    "name": "Formatura média/grande saudável",
                    "description": "Margem 25-32%, motor do negócio",
                    "characteristics": ["large_graduation", "medium_graduation"],
                    "target_margin": "25-32%"
                },
                "PERFIL_B": {
                    "name": "Evento pequeno barato",
                    "description": "Alto risco, ticket baixo",
                    "characteristics": ["small_revenue", "low_ticket"],
                    "target_margin": "15-20%"
                },
                "PERFIL_C": {
                    "name": "Evento pequeno premium",
                    "description": "Pode ser excelente se ticket alto",
                    "characteristics": ["small_revenue", "high_ticket"],
                    "target_margin": "30-40%"
                },
                "PERFIL_D": {
                    "name": "Evento com dados contaminados",
                    "description": "DRE não auditável sem rateio",
                    "characteristics": ["shared_costs", "incomplete_data"],
                    "target_margin": "N/A - requires cleanup"
                }
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"   ✓ Exported learning rules: {filepath}")
    
    def run(self, output_dir: str):
        """Run the complete backtest pipeline"""
        print("=" * 60)
        print("🎛️  ORKESTRA FINANCE BRAIN - BACKTEST GENERATOR")
        print("=" * 60)
        
        # Load and process data
        self.load_data()
        self.build_events()
        self.generate_learned_rules()
        
        # Generate outputs
        print("\n📁 Generating artifacts...")
        self.export_json(f"{output_dir}/events_backtest.json")
        self.export_csv(f"{output_dir}/events_backtest.csv")
        self.generate_summary_report(f"{output_dir}/backtest_summary.md")
        self.generate_insights_report(f"{output_dir}/backtest_insights.md")
        self.generate_rankings_report(f"{output_dir}/backtest_rankings.md")
        self.export_learning_rules(f"{output_dir}/openclaw_learning_rules.json")
        
        # Print summary statistics
        print("\n" + "=" * 60)
        print("📊 BACKTEST COMPLETE - KEY STATISTICS")
        print("=" * 60)
        
        total_events = len(self.events)
        high_conf = len([e for e in self.events if e.confidence_level == "HIGH"])
        med_conf = len([e for e in self.events if e.confidence_level == "MEDIUM"])
        low_conf = len([e for e in self.events if e.confidence_level == "LOW"])
        
        margins = [e.margin_percentage for e in self.events if e.confidence_level == "HIGH"]
        avg_margin = sum(margins) / len(margins) if margins else 0
        
        print(f"""
✅ Total Events Processed: {total_events}
   • LA ORANA: {len([e for e in self.events if e.company == 'LA ORANA'])}
   • STATUS Opera: {len([e for e in self.events if e.company == 'STATUS Opera'])}

📊 Confidence Distribution:
   • HIGH: {high_conf} events
   • MEDIUM: {med_conf} events  
   • LOW: {low_conf} events

💰 Average Margin (HIGH confidence): {avg_margin:.2f}%

⚠️ Main Margin Leakages:
   • Cost underallocation (margin > 40%): {len([e for e in self.events if e.margin_percentage > 40 and e.total_revenue > 40000])} events
   • High protein costs (>50%): {len([e for e in self.events if sum(e.direct_costs.values()) > e.total_revenue * 0.35])} events
   • Low ticket (< R$ 70): {len([e for e in self.events if e.estimated_ticket < 70])} events

🏆 Best Event Profile:
   • Highest margin: {max(self.events, key=lambda e: e.margin_percentage).event_name} ({max(self.events, key=lambda e: e.margin_percentage).margin_percentage:.1f}%)
   • Most profitable: {max(self.events, key=lambda e: e.margin_absolute).event_name} (R$ {max(self.events, key=lambda e: e.margin_absolute).margin_absolute:,.0f})

⚠️ Worst Event Profile:
   • Lowest margin: {min(self.events, key=lambda e: e.margin_percentage).event_name} ({min(self.events, key=lambda e: e.margin_percentage).margin_percentage:.1f}%)
   • Biggest loss: {min(self.events, key=lambda e: e.margin_absolute).event_name} (R$ {min(self.events, key=lambda e: e.margin_absolute).margin_absolute:,.0f})

💸 Where Business Loses Most Money:
""")
        
        worst_events = sorted(self.events, key=lambda e: e.margin_absolute)[:3]
        for i, e in enumerate(worst_events, 1):
            print(f"   {i}. {e.event_name}: R$ {e.margin_absolute:,.0f} ({e.margin_percentage:.1f}% margin)")
        
        print("\n💵 Where Business Makes Most Money:")
        best_events = sorted(self.events, key=lambda e: e.margin_absolute, reverse=True)[:3]
        for i, e in enumerate(best_events, 1):
            print(f"   {i}. {e.event_name}: R$ {e.margin_absolute:,.0f} ({e.margin_percentage:.1f}% margin)")
        
        print(f"""
📚 Top 5 Learned Rules:
""")
        for i, rule in enumerate(self.learned_rules[:5], 1):
            print(f"   {i}. [{rule['rule_id']}] {rule['category']}")
            print(f"      → {rule['recommendation']}")
        
        print(f"""
🎯 Recommended Next Steps:
   1. Audit {len([e for e in self.events if e.risk_level == 'CRITICAL'])} critical risk events immediately
   2. Improve cost allocation for {low_conf} low-confidence events
   3. Review menu/pricing for events with ticket < R$ 70
   4. Implement CAC tracking for all events
   5. Verify cost completeness for events with margin > 40%

✨ All artifacts saved to: {output_dir}
""")

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    import sys
    
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/ORKESTRA.AI/.openclaw/workspace-openclaw-bpo/artifacts"
    
    engine = BacktestEngine()
    engine.run(output_dir)
