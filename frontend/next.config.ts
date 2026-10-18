import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * `/ajustes/*` moved into `/reglas/*` (single settings area, T7.5 §2).
   * Old links/bookmarks still resolve instead of 404ing.
   */
  async redirects() {
    return [
      { source: "/ajustes", destination: "/reglas", permanent: true },
      { source: "/ajustes/politica", destination: "/reglas/politica", permanent: true },
      { source: "/ajustes/proveedores", destination: "/reglas/proveedores", permanent: true },
      {
        source: "/ajustes/proveedores/:nombre",
        destination: "/reglas/proveedores/:nombre",
        permanent: true,
      },
      { source: "/ajustes/acuerdos", destination: "/reglas/acuerdos", permanent: true },
      {
        source: "/ajustes/acuerdos/nuevo",
        destination: "/reglas/acuerdos/nuevo",
        permanent: true,
      },
      {
        source: "/ajustes/acuerdos/:proveedor",
        destination: "/reglas/acuerdos/:proveedor",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
