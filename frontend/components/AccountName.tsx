import { accountTextClass } from "@/lib/accountStyle";

export function AccountName({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  return <span className={`${accountTextClass(name)} ${className}`}>{name}</span>;
}
