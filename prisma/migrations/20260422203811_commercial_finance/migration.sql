-- AlterTable
ALTER TABLE "contracts" ADD COLUMN     "projectedMargin" DOUBLE PRECISION,
ADD COLUMN     "salesManagerId" TEXT,
ADD COLUMN     "salespersonId" TEXT,
ADD COLUMN     "sdrId" TEXT;

-- AlterTable
ALTER TABLE "proposals" ADD COLUMN     "discountAppliedPct" DOUBLE PRECISION NOT NULL DEFAULT 0,
ADD COLUMN     "discountAuthorizedAt" TIMESTAMP(3),
ADD COLUMN     "discountAuthorizedById" TEXT;

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "managerId" TEXT;

-- CreateTable
CREATE TABLE "contract_installments" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contractId" TEXT NOT NULL,
    "seq" INTEGER NOT NULL,
    "dueDate" TIMESTAMP(3) NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "paidAmount" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "status" TEXT NOT NULL DEFAULT 'PENDING',
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "contract_installments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "payments" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contractId" TEXT NOT NULL,
    "installmentId" TEXT,
    "amount" DOUBLE PRECISION NOT NULL,
    "paidAt" TIMESTAMP(3) NOT NULL,
    "method" TEXT NOT NULL,
    "externalRef" TEXT,
    "status" TEXT NOT NULL DEFAULT 'CONFIRMED',
    "note" TEXT,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "payments_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "commission_plans" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contractId" TEXT NOT NULL,
    "baseType" TEXT NOT NULL DEFAULT 'MARGIN',
    "baseAmount" DOUBLE PRECISION NOT NULL,
    "baseMarginPct" DOUBLE PRECISION,
    "signingPct" DOUBLE PRECISION NOT NULL DEFAULT 0.40,
    "installmentPct" DOUBLE PRECISION NOT NULL DEFAULT 0.60,
    "carencyDays" INTEGER NOT NULL DEFAULT 0,
    "managerOverridePct" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "sdrSplitPct" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "closerSplitPct" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    "discountAppliedPct" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "discountThreshold" DOUBLE PRECISION NOT NULL DEFAULT 0.10,
    "discountPenaltyPct" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "commissionPct" DOUBLE PRECISION NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdBy" TEXT,

    CONSTRAINT "commission_plans_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "commission_entries" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "contractId" TEXT NOT NULL,
    "installmentId" TEXT,
    "paymentId" TEXT,
    "userId" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "triggerType" TEXT NOT NULL,
    "amount" DOUBLE PRECISION NOT NULL,
    "baseAmount" DOUBLE PRECISION NOT NULL,
    "effectivePct" DOUBLE PRECISION NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'FORECAST',
    "scheduledFor" TIMESTAMP(3) NOT NULL,
    "releasedAt" TIMESTAMP(3),
    "paidAt" TIMESTAMP(3),
    "paidInPayrollId" TEXT,
    "clawedBackAt" TIMESTAMP(3),
    "clawbackReason" TEXT,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "commission_entries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bonus_rules" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "userId" TEXT,
    "role" TEXT,
    "periodType" TEXT NOT NULL DEFAULT 'MONTHLY',
    "effectiveFrom" TIMESTAMP(3) NOT NULL,
    "effectiveTo" TIMESTAMP(3),
    "rampUpMonths" INTEGER NOT NULL DEFAULT 0,
    "rampUpFactor" DOUBLE PRECISION NOT NULL DEFAULT 0.6,
    "maxPayout" DOUBLE PRECISION,
    "status" TEXT NOT NULL DEFAULT 'ACTIVE',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "bonus_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bonus_components" (
    "id" TEXT NOT NULL,
    "bonusRuleId" TEXT NOT NULL,
    "metric" TEXT NOT NULL,
    "weight" DOUBLE PRECISION NOT NULL,
    "target" DOUBLE PRECISION NOT NULL,
    "acceleratorBands" JSONB,
    "basePayout" DOUBLE PRECISION NOT NULL,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "bonus_components_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bonus_accruals" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "bonusRuleId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "periodStart" TIMESTAMP(3) NOT NULL,
    "periodEnd" TIMESTAMP(3) NOT NULL,
    "computedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "totalAmount" DOUBLE PRECISION NOT NULL,
    "breakdown" JSONB NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'COMPUTED',
    "approvedBy" TEXT,
    "approvedAt" TIMESTAMP(3),
    "paidAt" TIMESTAMP(3),
    "notes" TEXT,

    CONSTRAINT "bonus_accruals_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "provisioned_expenses" (
    "id" TEXT NOT NULL,
    "tenantId" TEXT NOT NULL,
    "sourceType" TEXT NOT NULL,
    "sourceId" TEXT NOT NULL,
    "beneficiaryId" TEXT,
    "amount" DOUBLE PRECISION NOT NULL,
    "forecastMonth" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'LOCKED',
    "reversedReason" TEXT,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "provisioned_expenses_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "contract_installments_tenantId_idx" ON "contract_installments"("tenantId");

-- CreateIndex
CREATE INDEX "contract_installments_status_idx" ON "contract_installments"("status");

-- CreateIndex
CREATE INDEX "contract_installments_dueDate_idx" ON "contract_installments"("dueDate");

-- CreateIndex
CREATE UNIQUE INDEX "contract_installments_contractId_seq_key" ON "contract_installments"("contractId", "seq");

-- CreateIndex
CREATE INDEX "payments_tenantId_idx" ON "payments"("tenantId");

-- CreateIndex
CREATE INDEX "payments_contractId_idx" ON "payments"("contractId");

-- CreateIndex
CREATE INDEX "payments_installmentId_idx" ON "payments"("installmentId");

-- CreateIndex
CREATE INDEX "payments_paidAt_idx" ON "payments"("paidAt");

-- CreateIndex
CREATE UNIQUE INDEX "commission_plans_contractId_key" ON "commission_plans"("contractId");

-- CreateIndex
CREATE INDEX "commission_plans_tenantId_idx" ON "commission_plans"("tenantId");

-- CreateIndex
CREATE INDEX "commission_entries_tenantId_idx" ON "commission_entries"("tenantId");

-- CreateIndex
CREATE INDEX "commission_entries_contractId_idx" ON "commission_entries"("contractId");

-- CreateIndex
CREATE INDEX "commission_entries_userId_status_idx" ON "commission_entries"("userId", "status");

-- CreateIndex
CREATE INDEX "commission_entries_status_scheduledFor_idx" ON "commission_entries"("status", "scheduledFor");

-- CreateIndex
CREATE INDEX "bonus_rules_tenantId_idx" ON "bonus_rules"("tenantId");

-- CreateIndex
CREATE INDEX "bonus_rules_userId_idx" ON "bonus_rules"("userId");

-- CreateIndex
CREATE INDEX "bonus_rules_status_idx" ON "bonus_rules"("status");

-- CreateIndex
CREATE INDEX "bonus_components_bonusRuleId_idx" ON "bonus_components"("bonusRuleId");

-- CreateIndex
CREATE INDEX "bonus_accruals_tenantId_idx" ON "bonus_accruals"("tenantId");

-- CreateIndex
CREATE INDEX "bonus_accruals_userId_status_idx" ON "bonus_accruals"("userId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "bonus_accruals_bonusRuleId_periodStart_periodEnd_key" ON "bonus_accruals"("bonusRuleId", "periodStart", "periodEnd");

-- CreateIndex
CREATE INDEX "provisioned_expenses_tenantId_forecastMonth_idx" ON "provisioned_expenses"("tenantId", "forecastMonth");

-- CreateIndex
CREATE INDEX "provisioned_expenses_sourceType_sourceId_idx" ON "provisioned_expenses"("sourceType", "sourceId");

-- CreateIndex
CREATE INDEX "provisioned_expenses_beneficiaryId_status_idx" ON "provisioned_expenses"("beneficiaryId", "status");

-- CreateIndex
CREATE INDEX "contracts_salespersonId_idx" ON "contracts"("salespersonId");

-- CreateIndex
CREATE INDEX "users_managerId_idx" ON "users"("managerId");

-- AddForeignKey
ALTER TABLE "proposals" ADD CONSTRAINT "proposals_discountAuthorizedById_fkey" FOREIGN KEY ("discountAuthorizedById") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contracts" ADD CONSTRAINT "contracts_salespersonId_fkey" FOREIGN KEY ("salespersonId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contracts" ADD CONSTRAINT "contracts_salesManagerId_fkey" FOREIGN KEY ("salesManagerId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contracts" ADD CONSTRAINT "contracts_sdrId_fkey" FOREIGN KEY ("sdrId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "users" ADD CONSTRAINT "users_managerId_fkey" FOREIGN KEY ("managerId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contract_installments" ADD CONSTRAINT "contract_installments_contractId_fkey" FOREIGN KEY ("contractId") REFERENCES "contracts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_contractId_fkey" FOREIGN KEY ("contractId") REFERENCES "contracts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "payments" ADD CONSTRAINT "payments_installmentId_fkey" FOREIGN KEY ("installmentId") REFERENCES "contract_installments"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "commission_plans" ADD CONSTRAINT "commission_plans_contractId_fkey" FOREIGN KEY ("contractId") REFERENCES "contracts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "commission_entries" ADD CONSTRAINT "commission_entries_contractId_fkey" FOREIGN KEY ("contractId") REFERENCES "contracts"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "commission_entries" ADD CONSTRAINT "commission_entries_installmentId_fkey" FOREIGN KEY ("installmentId") REFERENCES "contract_installments"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "commission_entries" ADD CONSTRAINT "commission_entries_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bonus_rules" ADD CONSTRAINT "bonus_rules_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bonus_components" ADD CONSTRAINT "bonus_components_bonusRuleId_fkey" FOREIGN KEY ("bonusRuleId") REFERENCES "bonus_rules"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bonus_accruals" ADD CONSTRAINT "bonus_accruals_bonusRuleId_fkey" FOREIGN KEY ("bonusRuleId") REFERENCES "bonus_rules"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "bonus_accruals" ADD CONSTRAINT "bonus_accruals_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

