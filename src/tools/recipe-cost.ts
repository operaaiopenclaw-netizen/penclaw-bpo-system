import { ToolImplementation, ToolExecutionInput, ToolExecutionOutput } from "../types/tools";
import { prisma } from "../db";
import { logger } from "../utils/logger";

/**
 * Tool: Recipe Cost Calculator
 * Calculates total cost for a recipe
 */
export class RecipeCostTool implements ToolImplementation {
  name = "recipe_cost_calculator";
  description = "Calculate total cost for a recipe with ingredients";

  async execute({ input }: ToolExecutionInput): Promise<ToolExecutionOutput> {
    const startTime = Date.now();
    
    logger.info("RecipeCostTool executing", { recipeId: input.recipeId });

    try {
      const recipeId = input.recipeId as string;
      const servings = input.servings as number || 1;
      
      // Fetch recipe
      const recipe = await prisma.recipe.findUnique({
        where: { id: recipeId }
      });

      if (!recipe) {
        return {
          success: false,
          data: null,
          error: `Recipe ${recipeId} not found`,
          latencyMs: Date.now() - startTime
        };
      }

      // Get ingredient costs
      const recipeData = JSON.parse(JSON.stringify(recipe.data || {})) as { ingredients: Array<{ itemId: string; quantity: number }> };
      
      const ingredientCosts = [];
      let totalCost = 0;

      for (const ing of recipeData.ingredients || []) {
        const item = await prisma.inventoryItem.findUnique({
          where: { id: ing.itemId }
        });
        
        if (item && item.weightedAverageCost) {
          const cost = item.weightedAverageCost * ing.quantity;
          totalCost += cost;
          ingredientCosts.push({
            name: item.name,
            quantity: ing.quantity,
            unitCost: item.weightedAverageCost,
            totalCost: cost
          });
        }
      }

      const costPerServing = servings > 0 ? totalCost / servings : totalCost;

      return {
        success: true,
        data: {
          recipe: { id: recipe.id, name: recipe.name },
          servings,
          totalCost,
          costPerServing,
          ingredientCosts,
          currency: "BRL"
        },
        latencyMs: Date.now() - startTime
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      
      logger.error("RecipeCostTool failed", { error: errorMessage });
      
      return {
        success: false,
        data: null,
        error: errorMessage,
        latencyMs: Date.now() - startTime
      };
    }
  }
}
