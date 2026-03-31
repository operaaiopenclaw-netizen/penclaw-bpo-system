-- Add analytics fields and tables

-- Recipe costs linking
CREATE TABLE IF NOT EXISTS recipe_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID REFERENCES recipes(id) ON DELETE CASCADE,
    total_cost DECIMAL(12, 2) DEFAULT 0,
    cost_per_portion DECIMAL(12, 2) DEFAULT 0,
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(recipe_id)
);

-- Add columns to inventory_items
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS min_stock_threshold DECIMAL(10, 3) DEFAULT 0;
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS max_stock_threshold DECIMAL(10, 3) DEFAULT 1000;
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS weighted_average_cost DECIMAL(12, 2) DEFAULT 0;
ALTER TABLE inventory_items ADD COLUMN IF NOT EXISTS last_purchase_price DECIMAL(12, 2) DEFAULT 0;

-- Add columns to recipes  
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS target_selling_price DECIMAL(12, 2);
ALTER TABLE recipes ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT true;
