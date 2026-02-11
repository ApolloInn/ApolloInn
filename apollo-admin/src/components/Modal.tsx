import { create } from "zustand";
import { useState, useEffect, useRef } from "react";

interface SelectOption {
  value: string;
  label: string;
}

interface ModalState {
  visible: boolean;
  type: "confirm" | "prompt" | "alert" | "select";
  title: string;
  message: string;
  defaultValue: string;
  options: SelectOption[];
  resolve: ((val: string | boolean | null) => void) | null;
  open: (opts: {
    type: "confirm" | "prompt" | "alert" | "select";
    title: string;
    message?: string;
    defaultValue?: string;
    options?: SelectOption[];
  }) => Promise<string | boolean | null>;
  close: (val: string | boolean | null) => void;
}

export const useModal = create<ModalState>((set, get) => ({
  visible: false,
  type: "alert",
  title: "",
  message: "",
  defaultValue: "",
  options: [],
  resolve: null,
  open: (opts) =>
    new Promise((resolve) => {
      set({
        visible: true,
        type: opts.type,
        title: opts.title,
        message: opts.message || "",
        defaultValue: opts.defaultValue || "",
        options: opts.options || [],
        resolve,
      });
    }),
  close: (val) => {
    const { resolve } = get();
    resolve?.(val);
    set({ visible: false, resolve: null });
  },
}));

export function confirm(title: string, message?: string) {
  return useModal.getState().open({ type: "confirm", title, message }) as Promise<boolean>;
}

export function prompt(title: string, defaultValue?: string) {
  return useModal.getState().open({ type: "prompt", title, defaultValue }) as Promise<string | null>;
}

export function alert(title: string, message?: string) {
  return useModal.getState().open({ type: "alert", title, message });
}

export function select(title: string, options: SelectOption[], defaultValue?: string, message?: string) {
  return useModal.getState().open({ type: "select", title, options, defaultValue, message }) as Promise<string | null>;
}

export function Modal() {
  const { visible, type, title, message, defaultValue, options, close } = useModal();
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (visible) setInput(defaultValue);
    if (visible && type === "prompt") setTimeout(() => inputRef.current?.focus(), 50);
  }, [visible, defaultValue, type]);

  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close(type === "confirm" ? false : null);
      if (e.key === "Enter" && type !== "prompt" && type !== "select") close(type === "confirm" ? true : null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [visible, type, close]);

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={() => close(type === "confirm" ? false : null)}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        {message && <div className="modal-message">{message}</div>}
        {type === "prompt" && (
          <input
            ref={inputRef}
            className="modal-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && close(input)}
          />
        )}
        {type === "select" && (
          <select
            className="modal-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          >
            {options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        )}
        <div className="modal-actions">
          {type === "confirm" && (
            <>
              <button className="btn btn-ghost" onClick={() => close(false)}>取消</button>
              <button className="btn btn-primary" onClick={() => close(true)}>确定</button>
            </>
          )}
          {(type === "prompt" || type === "select") && (
            <>
              <button className="btn btn-ghost" onClick={() => close(null)}>取消</button>
              <button className="btn btn-primary" onClick={() => close(input)}>确定</button>
            </>
          )}
          {type === "alert" && (
            <button className="btn btn-primary" onClick={() => close(null)}>确定</button>
          )}
        </div>
      </div>
    </div>
  );
}