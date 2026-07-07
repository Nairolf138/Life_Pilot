import { AuthenticatedLayout } from "@/components/authenticated-layout";
import "./styles.css";

export default function AppLayout({ children }: Readonly<{ children: import("react").ReactNode }>) {
  return <AuthenticatedLayout>{children}</AuthenticatedLayout>;
}
