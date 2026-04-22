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
      const rawIngredients = recipe.ingredients as { ingredients?: Array<{ itemId: string; quantity: number }> } | null;
      const ingredientList = rawIngredients?.ingredients ?? [];

      const ingredientCosts = [];
      let totalCost = 0;

      for (const ing of ingredientList) {
        const item = await prisma.inventoryItem.findUnique({
          where: { id: ing.itemId }
        });

        if (item && item.unitPrice) {
          const cost = item.unitPrice * ing.quantity;
          totalCost += cost;
          ingredientCosts.push({
            name: item.name,
            quantity: ing.quantity,
            unitCost: item.unitPrice,
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
