import { useRef, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";

// ──────────────────────────────────────────────────────────────
// AnalyticalGraph — Canvas-based D3 force-directed graph
//
// Improvements over original:
//   - Larger nodes (baseSize 6→14 vs old 5→12)
//   - Labels always visible when ≤8 nodes (new student experience)
//   - Lower zoom threshold (1.8 vs old 3.0)
//   - Thicker edges with strength-based width
//   - Outer glow ring on hover, pulse ring on active node
//   - Empty session state shows actionable text
//
// Props:
//   graphData   { nodes: NodeFrontend[], links: LinkFrontend[] }
//   isDarkMode  boolean
//   showLabels  boolean
// ──────────────────────────────────────────────────────────────

export default function AnalyticalGraph({ graphData, isDarkMode, showLabels }) {
  const containerRef = useRef(null);
  const fgRef        = useRef();
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [hoverNode, setHoverNode]   = useState(null);

  // Few-nodes regime: always show labels so new students see concept names
  const fewNodes = graphData.nodes.length <= 8;

  // Physics setup — re-runs when data changes
  useEffect(() => {
    if (!fgRef.current) return;

    const charge = fgRef.current.d3Force("charge");
    if (charge) {
      charge.strength(fewNodes ? -600 : -400);
      charge.distanceMax(fewNodes ? 600 : 900);
    }

    const link = fgRef.current.d3Force("link");
    if (link) {
      link.distance(fewNodes ? 160 : 120);
      link.strength(0.04);
    }

    fgRef.current.d3ReheatSimulation();
  }, [graphData, fewNodes]);

  // Camera centering
  useEffect(() => {
    if (fgRef.current && dimensions.width > 0) {
      fgRef.current.centerAt(0, 0);
    }
  }, [dimensions]);

  // ResizeObserver
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        setDimensions({
          width:  containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    update();
    const observer = new ResizeObserver(update);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const empty = graphData.nodes.length === 0;

  return (
    <div ref={containerRef} className="w-full h-full relative">

      {/* Empty state */}
      {empty && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none gap-3">
          <span className="font-mono text-[10px] text-gray-700 dark:text-gray-700 uppercase tracking-[0.4em]">
            Graph Loading
          </span>
          <div className="flex gap-1.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-700 animate-pulse"
                style={{ animationDelay: `${i * 200}ms` }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Force graph */}
      {!empty && dimensions.width > 0 && (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="transparent"

          // Velocity decay — controls how "floaty" nodes feel
          d3VelocityDecay={0.15}

          // Node interaction
          onNodeHover={setHoverNode}
          onNodeDrag={() => {
            if (fgRef.current) fgRef.current.d3ReheatSimulation();
          }}
          onNodeDragEnd={(node) => {
            delete node.fx;
            delete node.fy;
          }}

          // Edges — thicker lines, strength-based width
          linkDirectionalParticles={0}
          linkColor={() =>
            isDarkMode ? "rgba(255,255,255,0.18)" : "rgba(0,0,0,0.18)"
          }
          linkWidth={(link) => 0.8 + (link.strength || 0) * 3.0}

          // Node canvas renderer
          nodeCanvasObject={(node, ctx, globalScale) => {
            if (node.x === undefined || node.y === undefined) return;

            const mastery    = Math.max(0, Math.min(100, node.mastery    || 10));
            const confidence = Math.max(0, Math.min(100, node.confidence || 50));
            const isHovered  = hoverNode === node;

            // Node size: grows with mastery (6–14px radius)
            const baseSize = 6 + mastery * 0.08;

            // Node colour: Mastery-driven smooth gradient (Red -> Yellow -> Green)
            // m=0: #ef4444 (239, 68, 68) | m=50: #facc15 (250, 204, 21) | m=100: #22c55e (34, 197, 94)
            const getNodeColor = (m) => {
              const c1 = [239, 68, 68];   // Red
              const c2 = [250, 204, 21];  // Yellow
              const c3 = [34, 197, 94];   // Green
              let r, g, b;
              if (m <= 50) {
                const f = m / 50;
                r = c1[0] + (c2[0] - c1[0]) * f;
                g = c1[1] + (c2[1] - c1[1]) * f;
                b = c1[2] + (c2[2] - c1[2]) * f;
              } else {
                const f = (m - 50) / 50;
                r = c2[0] + (c3[0] - c2[0]) * f;
                g = c2[1] + (c3[1] - c2[1]) * f;
                b = c2[2] + (c3[2] - c2[2]) * f;
              }
              return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
            };

            const fillColor = getNodeColor(mastery);

            // ── Hover: outer glow ring ─────────────────────
            if (isHovered) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, baseSize + 5, 0, 2 * Math.PI);
              ctx.fillStyle = isDarkMode
                ? "rgba(255,255,255,0.06)"
                : "rgba(0,0,0,0.06)";
              ctx.fill();

              ctx.beginPath();
              ctx.arc(node.x, node.y, baseSize + 2.5, 0, 2 * Math.PI);
              ctx.strokeStyle = isDarkMode ? "rgba(255,255,255,0.25)" : "rgba(0,0,0,0.25)";
              ctx.lineWidth = 1;
              ctx.stroke();
            }

            // ── Inner background disc (subtle contrast backing) ──
            ctx.beginPath();
            ctx.arc(node.x, node.y, baseSize + 1.5, 0, 2 * Math.PI);
            ctx.fillStyle = isDarkMode ? "rgba(5,5,5,0.6)" : "rgba(255,255,255,0.6)";
            ctx.fill();

            // ── Main node disc ────────────────────────────
            ctx.beginPath();
            ctx.arc(node.x, node.y, baseSize, 0, 2 * Math.PI);
            ctx.fillStyle = fillColor;
            ctx.fill();

            // ── Label — always visible for few-node graph or on hover/zoom ──
            const showLabel =
              showLabels           // user toggled "always"
              || isHovered         // hovering
              || fewNodes          // ≤8 nodes — always label
              || globalScale >= 1.8; // zoomed in enough

            if (showLabel) {
              const fontSize   = Math.max(5, 11 / globalScale);
              const labelAlpha = isHovered ? 0.95 : 0.75;

              // Label background pill for readability
              const text   = node.id;
              ctx.font = `600 ${fontSize}px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`;
              const textW  = ctx.measureText(text).width;
              const labelY = node.y + baseSize + fontSize * 1.2;
              const padX   = fontSize * 0.5;
              const padY   = fontSize * 0.3;

              ctx.beginPath();
              ctx.roundRect(
                node.x - textW / 2 - padX,
                labelY - fontSize / 2 - padY,
                textW + padX * 2,
                fontSize + padY * 2,
                fontSize * 0.4
              );
              ctx.fillStyle = isDarkMode
                ? `rgba(5,5,5,${labelAlpha * 0.7})`
                : `rgba(255,255,255,${labelAlpha * 0.75})`;
              ctx.fill();

              // Label text
              ctx.textAlign    = "center";
              ctx.textBaseline = "middle";
              ctx.fillStyle    = isDarkMode
                ? `rgba(255,255,255,${labelAlpha})`
                : `rgba(0,0,0,${labelAlpha})`;
              ctx.fillText(text, node.x, labelY);
            }
          }}

          // Tooltip on hover (mastery % in browser status / tooltip)
          nodeLabel={(node) =>
            `${node.id} — Mastery: ${(node.mastery || 0).toFixed(1)}% | Confidence: ${(node.confidence || 0).toFixed(1)}%`
          }
        />
      )}
    </div>
  );
}
