export type AdminUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  groups: string[];
};

export type CidadaoUser = {
  id: number;
  cpf: string;
  nome_completo: string;
};

export type AuthResponse<TUser> = {
  access: string;
  refresh: string;
  user: TUser;
};

export type Especialidade = {
  id: number;
  nome: string;
  slug: string;
  tipo: string;
  tipo_display: string;
  ativo: boolean;
};

export type FiltroOpcao = {
  value: string | number;
  label: string;
};

export type FilaOpcoes = {
  especialidade_tipos: FiltroOpcao[];
  tipos: FiltroOpcao[];
  situacoes: FiltroOpcao[];
  prioridades: FiltroOpcao[];
};

export type RegistroFila = {
  id: number;
  publicacao_id: number;
  competencia: string;
  versao: number;
  especialidade_id: number;
  especialidade_nome: string;
  especialidade_slug: string;
  especialidade_tipo: string;
  especialidade_tipo_display: string;
  data_solicitacao: string;
  nome_mascarado: string;
  ano_nascimento: number | null;
  cpf_mascarado: string;
  cns_mascarado: string;
  sexo: string;
  codigo_solicitacao: string;
  posicao: number;
  prioridade: number;
  prioridade_display: string;
  tipo: string;
  tipo_display: string;
  situacao: string;
  situacao_display: string;
};
