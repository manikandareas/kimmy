import type {
  Activity,
  ChatEvent,
  Message,
  Run,
  Snapshot,
  ToolActivity,
} from "./api";

export const eventKinds = [
  "message.created",
  "run.queued",
  "run.running",
  "run.completed",
  "run.failed",
  "run.cancelled",
  "agent.text_delta",
  "tool.requested",
  "tool.completed",
];

export function applyEvent(state: Snapshot, event: ChatEvent): Snapshot {
  if (
    state.thread.id !== event.thread_id ||
    BigInt(event.seq) <= BigInt(state.through_seq)
  )
    return state;
  const next: Snapshot = {
    ...state,
    through_seq: event.seq,
    activities: [...(state.activities ?? [])],
  };
  const payload = event.payload;
  let activity = next.activities!.find((a) => a.run_id === event.run_id);
  if (event.kind.startsWith("run.")) {
    const run = payload.run as Run;
    next.latest_run = run;
    next.active_run = ["queued", "running"].includes(run.status) ? run : null;
    if (!activity) {
      activity = {
        run_id: run.id,
        message_id: run.message_id,
        text: "",
        tools: [],
        model_message_id: null,
      };
      next.activities!.push(activity);
    }
    if (event.kind === "run.queued")
      next.activities = next.activities!.map((a) =>
        a.run_id === run.id
          ? { ...a, text: "", tools: [], model_message_id: null }
          : a,
      );
    if (!next.active_run)
      next.activities = next.activities!.map((a) =>
        a.run_id === run.id
          ? {
              ...a,
              text: "",
              tools: a.tools?.map((tool) =>
                tool.status === "running"
                  ? { ...tool, status: "error" as const }
                  : tool,
              ),
            }
          : a,
      );
  } else if (event.kind === "message.created") {
    const message = payload.message as Message;
    if (!state.messages.some((m) => m.id === message.id))
      next.messages = [...state.messages, message];
    if (message.role === "assistant")
      next.activities = next.activities!.map((a) =>
        a.run_id === event.run_id ? { ...a, text: "" } : a,
      );
  } else if (activity) {
    let updated: Activity = { ...activity };
    if (event.kind === "agent.text_delta") {
      const modelId = payload.model_message_id as string | null;
      updated = {
        ...updated,
        model_message_id: modelId,
        text:
          (modelId === activity.model_message_id ? (activity.text ?? "") : "") +
          String(payload.text ?? ""),
      };
    } else if (event.kind.startsWith("tool.")) {
      const tool = payload as ToolActivity;
      updated.tools = [
        ...(activity.tools ?? []).filter(
          (t) => t.tool_call_id !== tool.tool_call_id,
        ),
        {
          ...tool,
          status: event.kind === "tool.requested" ? "running" : tool.status,
        },
      ];
    }
    next.activities = next.activities!.map((a) =>
      a.run_id === updated.run_id ? updated : a,
    );
  }
  return next;
}
