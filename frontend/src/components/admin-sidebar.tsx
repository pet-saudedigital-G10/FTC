"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Hospital, LayoutDashboard, ListFilter } from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { apiFetch } from "@/lib/api";
import { apiRoutes } from "@/lib/api-routes";
import type { SisregStatus } from "@/lib/api-types";

const items = [
  { title: "Visão geral", url: "/dashboard", icon: LayoutDashboard },
  { title: "Registros da fila", url: "/dashboard#registros", icon: ListFilter },
];

const sisregItem = {
  title: "Fila do SISREG",
  url: "/dashboard/sisreg",
  icon: Hospital,
};

export function AdminSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const [showSisreg, setShowSisreg] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadSisregStatus() {
      try {
        const status = await apiFetch<SisregStatus>(apiRoutes.sisregStatus, {
          cache: "no-store",
        });
        if (active) setShowSisreg(status.habilitado || status.pode_configurar);
      } catch {
        // The optional item stays hidden when the status is unavailable.
      }
    }
    void loadSisregStatus();
    return () => {
      active = false;
    };
  }, []);

  const menuItems = showSisreg ? [...items, sisregItem] : items;

  return (
    <Sidebar {...props}>
      <SidebarHeader className="border-b border-sidebar-border p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sidebar-foreground/60">
          Secretaria de Saúde
        </p>
        <p className="text-base font-semibold text-sidebar-foreground">
          Fila Transparente
        </p>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Gestão</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    isActive={pathname === item.url.split("#")[0]}
                    tooltip={item.title}
                    render={<Link href={item.url} />}
                  >
                    <item.icon />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}
