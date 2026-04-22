import { FastifyInstance } from "fastify";
import { z } from "zod";
import { userService } from "../services/user-service";
import { requirePermission, ROLES } from "../middleware/auth";
import { AppError } from "../utils/app-error";

const roleSchema = z.enum(ROLES as unknown as [string, ...string[]]);

const createSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1),
  password: z.string().min(8),
  role: roleSchema,
  tenantId: z.string().uuid().optional(),
});

const updateSchema = z.object({
  name: z.string().min(1).optional(),
  role: roleSchema.optional(),
  isActive: z.boolean().optional(),
  password: z.string().min(8).optional(),
});

export async function usersRoutes(app: FastifyInstance) {
  // All routes require admin
  app.addHook("preHandler", requirePermission("users.manage"));

  app.get("/", async (request) => {
    const tenantId = request.user!.tenantId;
    const users = await userService.listUsers(tenantId);
    return { users };
  });

  app.post("/", async (request, reply) => {
    const parsed = createSchema.safeParse(request.body);
    if (!parsed.success) {
      throw new AppError(
        `Invalid payload: ${parsed.error.errors.map((e) => e.message).join(", ")}`,
        400,
        "VALIDATION",
      );
    }
    const tenantId = parsed.data.tenantId ?? request.user!.tenantId;
    const user = await userService.createUser({
      tenantId,
      email: parsed.data.email,
      name: parsed.data.name,
      password: parsed.data.password,
      role: parsed.data.role as any,
    });
    return reply.code(201).send({ user });
  });

  app.patch("/:id", async (request) => {
    const { id } = request.params as { id: string };
    const parsed = updateSchema.safeParse(request.body);
    if (!parsed.success) {
      throw new AppError("Invalid payload", 400, "VALIDATION");
    }
    const user = await userService.updateUser(id, parsed.data as any);
    return { user };
  });

  app.delete("/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    if (id === request.user!.id) {
      throw new AppError("Cannot delete self", 400, "VALIDATION");
    }
    await userService.deleteUser(id);
    return reply.code(204).send();
  });
}
