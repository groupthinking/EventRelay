import { auth } from "@/app/(auth)/auth";
import { getDocumentsById } from "@/lib/db/queries";

export async function GET(request: Request) {
  const session = await auth();
  if (!session?.user?.id) return new Response("Authentication required", { status: 401 });
  const id = new URL(request.url).searchParams.get("id") ?? "";
  if (!/^[a-f0-9-]{36}$/i.test(id)) return new Response("Invalid guide id", { status: 400 });
  const rows = await getDocumentsById({ id });
  const doc = rows.at(-1);
  if (!doc || doc.userId !== session.user.id) return new Response("Guide not found", { status: 404 });
  return new Response(doc.content ?? "", { headers: { "Content-Type": "text/markdown; charset=utf-8", "Content-Disposition": 'attachment; filename="uvai-guide.md"', "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
}
