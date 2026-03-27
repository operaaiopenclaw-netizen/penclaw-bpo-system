# data_normalizer.py - Normalização Robusta de Dados Financeiros
# Orkestra Finance Brain

import pandas as pd


def normalize_columns(df):
    """Normaliza nomes de colunas para padrão internacional."""
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def map_value_column(df):
    """
    Mapeia colunas de valor de diferentes formatos para 'value'.
    Suporta: value, valor, amount
    """
    value_mappings = {
        "valor": "value",
        "amount": "value"
    }
    
    if "value" in df.columns:
        return df
    
    for col, new_col in value_mappings.items():
        if col in df.columns:
            df = df.rename(columns={col: new_col})
            return df
    
    raise ValueError(f"❌ Coluna de valor não encontrada. Disponíveis: {list(df.columns)}")


def clean_value_column(df, column="value"):
    """
    Limpa e converte valores monetários.
    Suporta formatos: R$ 1.000,00 | 1000.00 | 1,000.00
    """
    df[column] = (
        df[column]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace("R ", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    
    df[column] = pd.to_numeric(df[column], errors="coerce")
    
    return df


def remove_invalid_values(df, column="value"):
    """Remove linhas com valores inválidos (NaN após conversão)."""
    return df.dropna(subset=[column])


def normalize_type_column(df, column="type"):
    """
    Normaliza tipos de transação:
    - receita → income
    - despesa → expense
    - income/expense permanecem
    """
    df[column] = df[column].str.lower()
    
    df[column] = df[column].replace({
        "receita": "income",
        "recebimento": "income",
        "entrada": "income",
        "despesa": "expense",
        "pagamento": "expense",
        "saida": "expense",
        "saída": "expense"
    })
    
    return df


def normalize_categories(df, column="category"):
    """
    Normaliza categorias para padrão Orkestra.
    """
    category_map = {
        # Proteína
        "proteina": "protein",
        "proteína": "protein",
        "carne": "protein",
        "frango": "protein",
        "picanha": "protein",
        "alcatra": "protein",
        
        # Bebidas
        "bebidas": "beverages",
        "bebida": "beverages",
        "cerveja": "beverages",
        "refrigerante": "beverages",
        "agua": "beverages",
        "água": "beverages",
        "suco": "beverages",
        "destilado": "beverages",
        
        # Staff
        "staff": "staff",
        "garcom": "staff",
        "garçom": "staff",
        "bartender": "staff",
        "copeiro": "staff",
        "seguranca": "staff",
        "segurança": "staff",
        
        # Ambientação
        "ambientacao": "ambiance",
        "ambientação": "ambiance",
        "vela": "ambiance",
        "flores": "ambiance",
        "arranjo": "ambiance",
        "decoracao": "ambiance",
        "decoração": "ambiance",
        "iluminacao": "ambiance",
        "iluminação": "ambiance",
        
        # Material
        "material": "supplies",
        "copo": "supplies",
        "prato": "supplies",
        "talher": "supplies",
        "travessa": "supplies",
        "louca": "supplies",
        "louça": "supplies",
        
        # Infraestrutura
        "infraestrutura": "infrastructure",
        "mesa": "infrastructure",
        "cadeira": "infrastructure",
        "tenda": "infrastructure",
        "palco": "infrastructure",
        "estrutura": "infrastructure",
        
        # Evento/Receita
        "evento": "event",
        "receita": "event",
        "recebimento": "event"
    }
    
    df[column] = df[column].str.lower().replace(category_map)
    return df


def normalize_dataframe(df, value_col="value", type_col="type", category_col="category"):
    """
    Pipeline completo de normalização.
    """
    df = normalize_columns(df)
    df = map_value_column(df)
    df = clean_value_column(df, column=value_col)
    df = remove_invalid_values(df, column=value_col)
    df = normalize_type_column(df, column=type_col)
    
    if category_col in df.columns:
        df = normalize_categories(df, column=category_col)
    
    return df


# Exemplo de uso
if __name__ == "__main__":
    # Teste básico
    data = {
        "Tipo": ["Receita", "Despesa", "Despesa"],
        "Valor": ["R$ 9.000,00", "R$ 3.000,00", "R$ 1.500,00"],
        "Categoria": ["evento", "bebidas", "staff"],
        "Evento": ["Formatura", "Formatura", "Formatura"]
    }
    
    df = pd.DataFrame(data)
    print("Antes:")
    print(df)
    print("\nDepois:")
    print(normalize_dataframe(df))
