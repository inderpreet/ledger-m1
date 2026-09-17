import { redirect } from "next/navigation";

export default function OneOffRedirect() {
  redirect("/expenses/actual");
}
