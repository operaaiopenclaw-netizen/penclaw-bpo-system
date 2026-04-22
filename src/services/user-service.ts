import bcrypt from "bcrypt";
import jwt from "jsonwebtoken";
import { prisma } from "../db";
import { config } from "../config/env";
import { AppError } from "../utils/app-error";
import { ROLES, Role, AuthUser, JwtPayload } from "../middleware/auth";

const SALT_ROUNDS = 10;

export interface CreateUserInput {
  tenantId: string;
  email: string;
  name: string;
  password: string;
  role: Role;
}

export interface UpdateUserInput {
  name?: string;
  role?: Role;
  isActive?: boolean;
  password?: string;
}

function assertRole(role: string): asserts role is Role {
  if (!(ROLES as readonly string[]).includes(role)) {
    throw new AppError(`Invalid role: ${role}`, 400, "VALIDATION");
  }
}

function toAuthUser(u: {
  id: string;
  email: string;
  name: string;
  role: string;
  tenantId: string;
}): AuthUser {
  assertRole(u.role);
  return {
    id: u.id,
    email: u.email,
    name: u.name,
    role: u.role,
    tenantId: u.tenantId,
  };
}

export const userService = {
  async createUser(input: CreateUserInput) {
    assertRole(input.role);
    const email = input.email.trim().toLowerCase();
    const passwordHash = await bcrypt.hash(input.password, SALT_ROUNDS);
    try {
      return await prisma.user.create({
        data: {
          tenantId: input.tenantId,
          email,
          name: input.name,
          passwordHash,
          role: input.role,
        },
        select: {
          id: true,
          tenantId: true,
          email: true,
          name: true,
          role: true,
          isActive: true,
          lastLoginAt: true,
          createdAt: true,
        },
      });
    } catch (err: any) {
      if (err?.code === "P2002") {
        throw new AppError("Email already registered", 409, "CONFLICT");
      }
      throw err;
    }
  },

  async listUsers(tenantId: string) {
    return prisma.user.findMany({
      where: { tenantId },
      orderBy: { createdAt: "desc" },
      select: {
        id: true,
        tenantId: true,
        email: true,
        name: true,
        role: true,
        isActive: true,
        lastLoginAt: true,
        createdAt: true,
      },
    });
  },

  async updateUser(id: string, input: UpdateUserInput) {
    const data: Record<string, unknown> = {};
    if (input.name !== undefined) data.name = input.name;
    if (input.isActive !== undefined) data.isActive = input.isActive;
    if (input.role !== undefined) {
      assertRole(input.role);
      data.role = input.role;
    }
    if (input.password !== undefined) {
      data.passwordHash = await bcrypt.hash(input.password, SALT_ROUNDS);
    }
    return prisma.user.update({
      where: { id },
      data,
      select: {
        id: true,
        tenantId: true,
        email: true,
        name: true,
        role: true,
        isActive: true,
        lastLoginAt: true,
        createdAt: true,
      },
    });
  },

  async deleteUser(id: string) {
    await prisma.user.delete({ where: { id } });
  },

  async login(email: string, password: string) {
    const user = await prisma.user.findUnique({
      where: { email: email.trim().toLowerCase() },
    });
    if (!user || !user.isActive) {
      throw new AppError("Invalid credentials", 401, "UNAUTHORIZED");
    }
    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) {
      throw new AppError("Invalid credentials", 401, "UNAUTHORIZED");
    }
    await prisma.user.update({
      where: { id: user.id },
      data: { lastLoginAt: new Date() },
    });
    const authUser = toAuthUser(user);
    const token = this.signToken(authUser);
    return { user: authUser, token };
  },

  signToken(user: AuthUser): string {
    const payload: JwtPayload = { ...user };
    return jwt.sign(payload, config.JWT_SECRET, {
      expiresIn: config.JWT_EXPIRES_IN as any,
    });
  },

  async getById(id: string) {
    return prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        tenantId: true,
        email: true,
        name: true,
        role: true,
        isActive: true,
        lastLoginAt: true,
        createdAt: true,
      },
    });
  },
};
