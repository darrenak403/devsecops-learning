-- Supabase Postgres schema for OTP one-time verification workflow

create table if not exists users (
  id uuid primary key,
  email text not null unique,
  role_id uuid not null,
  is_active boolean not null default true,
  course_access_version int not null default 0,
  course_access_revoked_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists roles (
  id uuid primary key,
  name text not null unique,
  created_at timestamptz not null default now()
);

insert into roles (id, name)
values
  ('00000000-0000-0000-0000-000000000001', 'admin'),
  ('00000000-0000-0000-0000-000000000002', 'user')
on conflict (name) do nothing;

alter table users
  add constraint fk_users_role_id foreign key (role_id) references roles(id);

create index if not exists idx_users_role_id on users(role_id);

create table if not exists otp_tokens (
  id uuid primary key,
  otp_value text not null,
  otp_hash text not null,
  otp_hint text not null,
  issued_by_user_id uuid null references users(id),
  version int not null,
  ttl_seconds int not null,
  is_active boolean not null default true,
  used_at timestamptz null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_otp_tokens_active on otp_tokens(is_active);
create index if not exists idx_otp_tokens_expires_at on otp_tokens(expires_at);

create table if not exists otp_verifications (
  id uuid primary key,
  user_id uuid not null references users(id),
  otp_token_id uuid not null unique references otp_tokens(id),
  created_at timestamptz not null default now()
);
create index if not exists idx_otp_verifications_user_id on otp_verifications(user_id);
create index if not exists idx_otp_verifications_created_at on otp_verifications(created_at);
