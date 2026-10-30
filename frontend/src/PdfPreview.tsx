import { useEffect, useRef, useState } from "react";
import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { request } from "./api";
import type { Passage } from "./types";
GlobalWorkerOptions.workerSrc = workerUrl;

export function PdfPreview({ passage }: { passage: Passage }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [regions, setRegions] = useState<
    { left: number; top: number; width: number; height: number }[]
  >([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let disposed = false;
    let destroy: (() => void) | undefined;
    setLoading(true);
    setError("");
    setRegions([]);
    async function render() {
      const response = passage.pdf_url
        ? await fetch(passage.pdf_url)
        : await request(`/versions/${passage.version_id}/pdf`);
      if (!response.ok) throw new Error("Source PDF is unavailable");
      const task = getDocument({
        data: new Uint8Array(await response.arrayBuffer()),
        isEvalSupported: false,
      });
      destroy = () => {
        void task.destroy();
      };
      const doc = await task.promise;
      const page = await doc.getPage(passage.page);
      const viewport = page.getViewport({ scale: 1 });
      if (disposed || !canvas.current) return;
      canvas.current.width = viewport.width;
      canvas.current.height = viewport.height;
      const context = canvas.current.getContext("2d");
      if (!context) throw new Error("Canvas unavailable");
      await page.render({ canvasContext: context, viewport }).promise;
      if (disposed) return;
      const highlights = passage.boxes
        .filter((b) => b.page === passage.page)
        .map(({ bbox: b }) => {
          const topOrigin = b.coord_origin?.toUpperCase().includes("TOP");
          const rect = viewport.convertToViewportRectangle([
            b.l,
            topOrigin ? page.view[3] - b.t : b.t,
            b.r,
            topOrigin ? page.view[3] - b.b : b.b,
          ]);
          return {
            left: (Math.min(rect[0], rect[2]) / viewport.width) * 100,
            top: (Math.min(rect[1], rect[3]) / viewport.height) * 100,
            width: (Math.abs(rect[0] - rect[2]) / viewport.width) * 100,
            height: (Math.abs(rect[1] - rect[3]) / viewport.height) * 100,
          };
        });
      setRegions(highlights);
      setLoading(false);
    }
    void render().catch(() => {
      if (!disposed) {
        setError(
          "PDF preview unavailable. The stored page and exact passage remain inspectable below.",
        );
        setLoading(false);
      }
    });
    return () => {
      disposed = true;
      destroy?.();
    };
  }, [passage]);
  return (
    <div className="pdf-shell">
      {loading && <p className="muted">Loading original page…</p>}
      {error && <p role="status">{error}</p>}
      <div className="pdf-page">
        <canvas ref={canvas} aria-label={`Original PDF page ${passage.page}`} />
        {regions.map((r, i) => (
          <div
            key={i}
            className="source-highlight"
            style={{
              left: r.left + "%",
              top: r.top + "%",
              width: r.width + "%",
              height: r.height + "%",
            }}
          />
        ))}
      </div>
    </div>
  );
}
