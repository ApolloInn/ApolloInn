import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

export function StreamingMessage({ text }: { text: string }) {
  return (
    <div className="message aurora">
      <div className="message-bubble">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {text}
        </ReactMarkdown>
      </div>
      <div className="message-meta">Aurora Core · streaming...</div>
    </div>
  );
}
