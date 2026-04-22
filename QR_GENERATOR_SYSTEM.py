#!/usr/bin/env python3
"""
QR CODE GENERATOR SYSTEM — Orkestra Stock Mobile
Gera QR codes para: itens, kits, eventos, caixas logísticas
Formato: PNG para impressão + SVG para web
"""

import qrcode
from qrcode.constants import ERROR_CORRECT_M
import json
import uuid
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import hashlib

# Configurações de layout
LAYOUTS = {
    'item': {
        'size': 400,
        'box_size': 10,
        'border': 2,
        'label_height': 80
    },
    'kit': {
        'size': 400,
        'box_size': 10,
        'border': 2,
        'label_height': 120
    },
    'event': {
        'size': 600,
        'box_size': 10,
        'border': 3,
        'label_height': 100
    },
    'box': {
        'size': 500,
        'box_size': 10,
        'border': 3,
        'label_height': 100
    }
}

COLORS = {
    'qopera': {'bg': '#1e3a5f', 'text': '#ffffff'},      # Azul escuro
    'laohana': {'bg': '#5a2d2d', 'text': '#ffffff'},     # Vinho
    'robusta': {'bg': '#2d5a3d', 'text': '#ffffff'},      # Verde
    'general': {'bg': '#333333', 'text': '#ffffff'}        # Cinza
}

class QRGenerator:
    """Gerador de QR Codes para Orkestra"""
    
    def __init__(self, company='general'):
        self.company = company
        self.colors = COLORS.get(company, COLORS['general'])
        
    def generate_item_qr(self, item_id, sku, name, item_type='patrimonio', unit='unidade'):
        """
        Gera QR para item individual
        
        Args:
            item_id: UUID do item
            sku: Código SKU
            name: Nome do item
            item_type: Tipo (patrimonio, consumo, insumo)
            unit: Unidade (unidade, kg, m, etc)
        """
        
        # Payload estruturado
        payload = {
            'version': '1.0',
            'type': 'ORKESTRA-ITEM',
            'item_id': str(item_id),
            'sku': sku,
            'name': name[:30],  # Limita para URL segura
            'item_type': item_type,
            'unit': unit,
            'company': self.company,
            'generated_at': datetime.now().isoformat(),
            'checksum': self._generate_checksum(item_id, sku)
        }
        
        # Converte para string JSON compacta
        qr_data = json.dumps(payload, separators=(',', ':'))
        
        # Gera QR
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=LAYOUTS['item']['box_size'],
            border=LAYOUTS['item']['border']
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Cria imagem
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Adiciona label
        final_img = self._add_label(qr_img, sku, name, 'item')
        
        return {
            'image': final_img,
            'data': qr_data,
            'payload': payload,
            'file_name': f"QR-ITEM-{sku}.png"
        }
    
    def generate_kit_qr(self, kit_id, kit_name, items, client=''):
        """
        Gera QR para kit (conjunto de itens)
        
        Args:
            kit_id: UUID do kit
            kit_name: Nome do kit
            items: Lista de dicts {item_id, qty, name}
            client: Cliente do kit (opcional)
        """
        
        payload = {
            'version': '1.0',
            'type': 'ORKESTRA-KIT',
            'kit_id': str(kit_id),
            'kit_name': kit_name[:40],
            'items': [
                {
                    'id': str(item['item_id']),
                    'qty': item['qty'],
                    'name': item['name'][:15]
                }
                for item in items[:20]  # Limita 20 itens
            ],
            'total_items': sum(i['qty'] for i in items),
            'client': client[:20] if client else '',
            'company': self.company,
            'generated_at': datetime.now().isoformat(),
            'checksum': self._generate_checksum(kit_id, kit_name)
        }
        
        qr_data = json.dumps(payload, separators=(',', ':'))
        
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_M,
            box_size=LAYOUTS['kit']['box_size'],
            border=LAYOUTS['kit']['border']
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        final_img = self._add_label(qr_img, f"KIT-{kit_id[:8]}", kit_name, 'kit')
        
        return {
            'image': final_img,
            'data': qr_data,
            'payload': payload,
            'file_name': f"QR-KIT-{str(kit_id)[:8]}.png"
        }
    
    def generate_event_qr(self, event_id, ctt, client, event_date, company=''):
        """
        Gera QR para identificação de evento
        
        Args:
            event_id: UUID do evento
            ctt: Código CTT (ex: CTT-2025-0456)
            client: Nome do cliente
            event_date: Data do evento
            company: Empresa executora
        """
        
        payload = {
            'version': '1.0',
            'type': 'ORKESTRA-EVENT',
            'event_id': str(event_id),
            'ctt': ctt,
            'client': client[:40],
            'event_date': event_date.isoformat() if hasattr(event_date, 'isoformat') else event_date,
            'company': company or self.company,
            'generated_at': datetime.now().isoformat(),
            'checksum': self._generate_checksum(event_id, ctt)
        }
        
        qr_data = json.dumps(payload, separators=(',', ':'))
        
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_M,
            box_size=LAYOUTS['event']['box_size'],
            border=LAYOUTS['event']['border']
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Label maior para eventos
        label_text = f"{ctt}\n{client[:20]}"
        final_img = self._add_label(qr_img, ctt, label_text, 'event')
        
        return {
            'image': final_img,
            'data': qr_data,
            'payload': payload,
            'file_name': f"QR-EVENT-{ctt}.png"
        }
    
    def generate_logistics_box_qr(self, box_id, event_id, contents, weight_kg=0):
        """
        Gera QR para caixa logística
        
        Args:
            box_id: UUID da caixa
            event_id: UUID do evento
            contents: Lista de itens na caixa
            weight_kg: Peso em kg
        """
        
        # Hash do conteúdo para verificação
        contents_hash = hashlib.sha256(
            json.dumps(contents, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        payload = {
            'version': '1.0',
            'type': 'ORKESTRA-BOX',
            'box_id': str(box_id),
            'event_id': str(event_id),
            'contents_count': len(contents),
            'contents_hash': contents_hash,
            'weight_kg': weight_kg,
            'company': self.company,
            'generated_at': datetime.now().isoformat(),
            'checksum': self._generate_checksum(box_id, contents_hash)
        }
        
        qr_data = json.dumps(payload, separators=(',', ':'))
        
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT_M,
            box_size=LAYOUTS['box']['box_size'],
            border=LAYOUTS['box']['border']
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        label = f"CAIXA-{str(box_id)[:6]}\n{len(contents)} itens"
        final_img = self._add_label(qr_img, f"BOX-{str(box_id)[:6]}", label, 'box')
        
        return {
            'image': final_img,
            'data': qr_data,
            'payload': payload,
            'file_name': f"QR-BOX-{str(box_id)[:8]}.png"
        }
    
    def _add_label(self, qr_img, code, name, layout_type):
        """Adiciona label abaixo do QR code"""
        
        # Configurações do layout
        config = LAYOUTS[layout_type]
        label_height = config['label_height']
        
        # Cria imagem final com espaço para label
        qr_width, qr_height = qr_img.size
        total_height = qr_height + label_height
        
        final_img = Image.new(
            'RGB',
            (qr_width, total_height),
            self.colors['bg']
        )
        
        # Cola QR no topo
        final_img.paste(qr_img, (0, 0))
        
        # Desenha label
        draw = ImageDraw.Draw(final_img)
        
        # Linha separadora
        draw.line([(0, qr_height), (qr_width, qr_height)], fill='white', width=2)
        
        # Código em destaque
        try:
            font_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            font_code = ImageFont.load_default()
            font_name = ImageFont.load_default()
        
        # Centraliza código
        bbox = draw.textbbox((0, 0), code, font=font_code)
        text_width = bbox[2] - bbox[0]
        x_code = (qr_width - text_width) // 2
        
        draw.text((x_code, qr_height + 10), code, fill=self.colors['text'], font=font_code)
        
        # Nome quebrado em linhas
        lines = self._wrap_text(name, 25)[:2]  # Max 2 linhas
        y_name = qr_height + 40
        for line in lines:
            draw.text((10, y_name), line, fill=self.colors['text'], font=font_name)
            y_name += 20
        
        return final_img
    
    def _wrap_text(self, text, max_chars):
        """Quebra texto em linhas"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text[:max_chars]]
    
    def _generate_checksum(self, *args):
        """Gera checksum simples para validação"""
        data = ''.join(str(a) for a in args)
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    
    def save(self, result, output_dir='./qr_codes/'):
        """Salva QR em arquivo"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, result['file_name'])
        result['image'].save(file_path, 'PNG', quality=95)
        
        return file_path


# Exemplo de uso
if __name__ == '__main__':
    
    # Inicializa gerador
    gen = QRGenerator(company='qopera')
    
    # 1. Item individual
    item = gen.generate_item_qr(
        item_id=uuid.uuid4(),
        sku='CAD-BRA-STD',
        name='Cadeira Padrão Branca',
        item_type='patrimonio',
        unit='unidade'
    )
    gen.save(item, './qrs/')
    print(f"✅ QR Item salvo: {item['file_name']}")
    
    # 2. Kit casamento
    kit_items = [
        {'item_id': uuid.uuid4(), 'qty': 100, 'name': 'Cadeira'},
        {'item_id': uuid.uuid4(), 'qty': 50, 'name': 'Mesa 8L'},
        {'item_id': uuid.uuid4(), 'qty': 100, 'name': 'Prato'},
    ]
    kit = gen.generate_kit_qr(
        kit_id=uuid.uuid4(),
        kit_name='Kit Casamento 100p Premium',
        items=kit_items,
        client='Casamento Silva'
    )
    gen.save(kit, './qrs/')
    print(f"✅ QR Kit salvo: {kit['file_name']}")
    
    # 3. Evento
    from datetime import date
    event = gen.generate_event_qr(
        event_id=uuid.uuid4(),
        ctt='CTT-2025-0456',
        client='Maria Silva - Casamento',
        event_date=date(2025, 4, 15),
        company='qopera'
    )
    gen.save(event, './qrs/')
    print(f"✅ QR Evento salvo: {event['file_name']}")
    
    # 4. Caixa logística
    box = gen.generate_logistics_box_qr(
        box_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        contents=[{'item': 'cadeira', 'qty': 20}],
        weight_kg=45
    )
    gen.save(box, './qrs/')
    print(f"✅ QR Caixa salvo: {box['file_name']}")
    
    print("\n🎛️ Sistema de QR Codes Orkestra — Pronto para impressão!")
