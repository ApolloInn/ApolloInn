export function TasksView() {
  return (
    <>
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="material-symbols-rounded" style={{ color: "var(--color-primary)" }}>task_alt</span>
          <span className="chat-header-title">Task Operations Board</span>
        </div>
      </div>

      <div className="task-board">
        <TaskColumn title="Running" count={0} id="running" />
        <TaskColumn title="Pending" count={0} id="pending" />
        <TaskColumn title="Completed" count={0} id="completed" />
      </div>
    </>
  );
}

function TaskColumn({ title, count, id }: { title: string; count: number; id: string }) {
  return (
    <div className="task-column">
      <div className="task-column-header">
        {title} <span className="task-column-count">{count}</span>
      </div>
      <div className="task-column-body">
        {count === 0 && (
          <div className="empty-state" style={{ padding: 20 }}>
            <span className="material-symbols-rounded" style={{ fontSize: 32 }}>inbox</span>
            <p>No {id} tasks</p>
          </div>
        )}
      </div>
    </div>
  );
}
