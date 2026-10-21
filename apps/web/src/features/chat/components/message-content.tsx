import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "../api";

export function MessageContent({
  content,
  citations = [],
  onSource,
}: {
  content: string;
  citations?: Citation[];
  onSource?: (citation: Citation) => void;
}) {
  const text = content
    .replace(/\[SOP:([^\]]*)\]/g, (_, id: string) => {
      const index = citations.findIndex((c) => c.chunk_id === id);
      return index < 0 ? "" : `[Sumber ${index + 1}](#source-${id})`;
    })
    .replace(/\[SOP:[^\]]*$/, "");
  return (
    <div className="message-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const citation = citations.find(
              (c) => href === `#source-${c.chunk_id}`,
            );
            if (citation)
              return (
                <button
                  type="button"
                  className="citation-link"
                  onClick={() => onSource?.(citation)}
                >
                  {children}
                </button>
              );
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
