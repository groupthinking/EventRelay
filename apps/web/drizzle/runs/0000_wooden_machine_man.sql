CREATE TABLE "uvai_run_approvals" (
	"run_id" text NOT NULL,
	"spec_hash" text NOT NULL,
	"spec_revision" integer NOT NULL,
	"approver_id" text NOT NULL,
	"approved_spec" jsonb NOT NULL,
	"approved_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "uvai_run_approvals_run_id_spec_revision_pk" PRIMARY KEY("run_id","spec_revision")
);
--> statement-breakpoint
CREATE TABLE "uvai_run_events" (
	"id" text PRIMARY KEY NOT NULL,
	"run_id" text NOT NULL,
	"revision" integer NOT NULL,
	"kind" text NOT NULL,
	"actor_id" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "uvai_run_members" (
	"tenant_id" text NOT NULL,
	"user_id" text NOT NULL,
	"role" text NOT NULL,
	CONSTRAINT "uvai_run_members_tenant_id_user_id_pk" PRIMARY KEY("tenant_id","user_id")
);
--> statement-breakpoint
CREATE TABLE "uvai_runs" (
	"id" text PRIMARY KEY NOT NULL,
	"tenant_id" text NOT NULL,
	"project_id" text NOT NULL,
	"status" text NOT NULL,
	"revision" integer DEFAULT 1 NOT NULL,
	"spec" jsonb NOT NULL,
	"spec_hash" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "uvai_run_approvals" ADD CONSTRAINT "uvai_run_approvals_run_id_uvai_runs_id_fk" FOREIGN KEY ("run_id") REFERENCES "public"."uvai_runs"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "uvai_run_events" ADD CONSTRAINT "uvai_run_events_run_id_uvai_runs_id_fk" FOREIGN KEY ("run_id") REFERENCES "public"."uvai_runs"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "uvai_run_event_revision" ON "uvai_run_events" USING btree ("run_id","revision");