import { FastifyInstance } from "fastify";
import { z } from "zod";
import { userService } from "../services/user-service";
import { authenticate } from "../middleware/auth";
import { AppError } from "../utils/app-error";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export async function authRoutes(app: FastifyInstance) {
  app.post("/login", async (request, reply) => {
    const parsed = loginSchema.safeParse(request.body);
    if (!parsed.success) {
      throw new AppError("Invalid login payload", 400, "VALIDATION");
    }
    const { user, token } = await userService.login(
      parsed.data.email,
      parsed.data.password,
    );
    return reply.send({ user, token });
  });

  app.get("/me", { preHandler: authenticate }, async (request) => {
    if (!request.user) {
      throw new AppError("Unauthenticated", 401, "UNAUTHORIZED");
    }
    const fresh = await userService.getById(request.user.id);
    return { user: fresh ?? request.user };
  });

  // Logout is client-side (drop token). Endpoint exists for audit + symmetry.
  app.post("/logout", { preHandler: authenticate }, async () => {
    return { ok: true };
  });
}
