import { auth } from "@/app/(auth)/auth";

export async function POST() {
  const session = await auth();
  if (!session?.user?.id) return Response.json({ error: "authentication_required" }, { status: 401 });
  return Response.json({ error: "uploads_not_enabled", message: "Only supported YouTube URLs are available in this foundation integration." }, { status: 501 });
}
