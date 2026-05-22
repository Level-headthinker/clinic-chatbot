import { Inbox } from "lucide-react";

export default function EmptyState({ icon, title, description, action }) {
  const Icon = icon || Inbox;
  return (
    <div className="empty-state">
      <div className="empty-mark">
        <Icon size={24} />
      </div>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}
