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

export type SisregStatus = {
  habilitado: boolean;
  ambiente: string | null;
  indice: string | null;
  pode_configurar: boolean;
};

export type SisregConfiguracao = {
  habilitado: boolean;
  ambiente: string;
  client_id: string;
  indice: string;
  centrais_reguladoras: string[];
  client_secret_configurado: boolean;
  atualizado_em: string | null;
};

export type SisregTesteConexao = {
  total: number;
};

export type SisregGrupo = {
  codigo: string;
  nome: string;
  total: number;
};

export type SisregGrupos = {
  total: number;
  grupos: SisregGrupo[];
};

export type SisregRegistro = {
  codigo_solicitacao: string;
  data_solicitacao: string;
  nome_mascarado: string;
  cns_mascarado: string;
  codigo_grupo_procedimento: string;
  nome_grupo_procedimento: string;
  classificacao_risco: string;
  situacao: string;
  situacao_display: string;
};

export type SisregFila = {
  total: number;
  pagina: number;
  tamanho_pagina: number;
  registros: SisregRegistro[];
};

export type PublicacaoImportada = {
  publicacao_id: number;
  especialidade_id: number;
  competencia: string;
  versao: number;
  status: string;
  registros_importados: number;
  publicacoes_substituidas: number[];
  importado_em: string;
  publicada_em: string;
};

export type TransparenciaContagem = {
  valor: string | number;
  rotulo: string;
  total: number;
};

export type TransparenciaEspecialidade = {
  nome: string;
  tipo: string;
  total: number;
  espera_media_dias: number | null;
  maior_espera_dias: number;
};

export type TransparenciaIndicadores = {
  atualizado_em: string | null;
  total_aguardando: number;
  especialidades_com_fila: number;
  espera_media_dias: number | null;
  maior_espera_dias: number;
  por_tipo: TransparenciaContagem[];
  por_prioridade: TransparenciaContagem[];
  por_situacao: TransparenciaContagem[];
  especialidades: TransparenciaEspecialidade[];
};

export type TransparenciaPosicao = {
  encontrado: boolean;
  filas: {
    especialidade: string;
    tipo: string;
    posicao: number;
    total_aguardando: number;
    situacao: string;
    prioridade: string;
    data_solicitacao: string;
    dias_espera: number;
    atualizado_em: string | null;
  }[];
};
