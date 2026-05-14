"use client";

import { useTheme } from "@/lib/providers/themeProvider";
import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

export function Toaster(props: ToasterProps) {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      toastOptions={{
        style: {
          borderRadius: "12px"
        }
      }}
      {...props}
    />
  );
}
