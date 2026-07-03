import { useEffect, useState } from "react"
import { EditorContent, useEditor } from "@tiptap/react"
import StarterKit from "@tiptap/starter-kit"
import { Bold, Code, Italic, List, ListOrdered, Redo, Undo } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type Props = { value: string; onChange: (html: string) => void }

export function RichTextEditor({ value, onChange }: Props) {
  const [raw, setRaw] = useState(false)
  const editor = useEditor({
    extensions: [StarterKit],
    content: value,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  })

  // Resync when value changes externally (Discard, Re-pull) — editor seeds content
  // only at mount otherwise. Guard against the echo from our own onUpdate.
  useEffect(() => {
    if (editor && !raw && value !== editor.getHTML()) {
      editor.commands.setContent(value, { emitUpdate: false })
    }
  }, [value, editor, raw])

  if (!editor) return null

  const Btn = ({ active, onClick, children }: { active?: boolean; onClick: () => void; children: React.ReactNode }) => (
    <Button type="button" variant="ghost" size="sm" className={cn(active && "bg-accent")} onClick={onClick}>
      {children}
    </Button>
  )

  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-0.5 border-b bg-muted/40 px-1 py-0.5">
        <Btn active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()}>
          <Bold className="size-4" />
        </Btn>
        <Btn active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()}>
          <Italic className="size-4" />
        </Btn>
        <Btn
          active={editor.isActive("heading", { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          H2
        </Btn>
        <Btn
          active={editor.isActive("heading", { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          H3
        </Btn>
        <Btn active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()}>
          <List className="size-4" />
        </Btn>
        <Btn active={editor.isActive("orderedList")} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
          <ListOrdered className="size-4" />
        </Btn>
        <Btn onClick={() => editor.chain().focus().undo().run()}>
          <Undo className="size-4" />
        </Btn>
        <Btn onClick={() => editor.chain().focus().redo().run()}>
          <Redo className="size-4" />
        </Btn>
        <Btn
          active={raw}
          onClick={() => {
            if (raw) editor.commands.setContent(value)
            setRaw(!raw)
          }}
        >
          <Code className="size-4" /> HTML
        </Btn>
      </div>
      {raw ? (
        <Textarea
          className="min-h-40 rounded-none border-0 font-mono text-xs"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <EditorContent editor={editor} className="prose prose-sm max-w-none px-3 py-2 [&_.ProseMirror]:min-h-40 [&_.ProseMirror]:outline-none" />
      )}
    </div>
  )
}
