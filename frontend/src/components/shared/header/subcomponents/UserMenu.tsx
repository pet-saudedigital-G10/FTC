import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/components/ui/avatar";

interface UserMenuProps {
  name: string;
  role?: string;
  avatarUrl?: string;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
}

export function UserMenu({ name, role, avatarUrl }: UserMenuProps) {
  const displayName = role ? `${role}: ${name}` : name;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-white/90 hidden sm:block">
        {displayName}
      </span>
      <Avatar className="w-9 h-9 border-2 border-white/30">
        {avatarUrl && <AvatarImage src={avatarUrl} alt={name} />}
        <AvatarFallback className="bg-white/20 text-white text-xs font-semibold">
          {getInitials(name)}
        </AvatarFallback>
      </Avatar>
    </div>
  );
}
