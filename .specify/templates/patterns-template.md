# Project Patterns

**Gerado por**: `/speckit-scan`  
**Data**: [DATA_ISO]

> As seções marcadas com ⚠️ são inferidas por amostragem de código — revisar antes de tratar como autoridade.

---

## [SUBREPO] — ex.: vale-base-volumes-mfe/front (React/TypeScript)

### Estrutura de Diretórios

| Tipo de artefato     | Caminho relativo ao workspace |
|----------------------|-------------------------------|
| Componentes React    | `[caminho]/components/`       |
| Hooks customizados   | `[caminho]/hooks/`            |
| Testes unitários     | `[caminho]/__tests__/`        |
| Páginas/views        | `[caminho]/pages/`            |
| State (Redux slices) | `[caminho]/store/`            |

### Convenções de Nomenclatura

> ⚠️ Inferido por amostragem.

- Componentes: [PascalCase | kebab-case | detectado]
- Hooks: [prefixo `use` + camelCase | detectado]
- Test files: [padrão detectado: `.test.tsx`, `.spec.ts`]
- Padrões específicos detectados: [ex.: `useGetXxx` para queries, `useXxxMutation` para mutações | N/A]

### Composição Interna

> ⚠️ Inferido por amostragem de 2-3 arquivos de cada tipo.

**Componente React:**
- Props interface: [antes do componente | inline no parâmetro | detectado]
- Export: [default export | named export | detectado]
- Styled components: [inline | arquivo separado `ComponentName.styles.ts` | não usa | detectado]
- Ordem interna: [detectado — ex.: imports → interface → component → helpers → export]

**Custom Hook:**
- Estrutura: [detectado — ex.: estado local → efeitos → retorno de objeto explícito]

### Padrões Relacionais

> ⚠️ Inferido por amostragem de imports.

- Import style: [relativo `../../components` | absoluto via alias `@components/` | detectado]
- Barrel files (index.ts): [sim — cada feature expõe API pública via index.ts | não | detectado]
- Fronteira de módulo: [imports apenas via index.ts | imports diretos permitidos | detectado]

### Soluções para Problemas Recorrentes

> ⚠️ Inferido por presença de arquivos de setup e amostragem de uso.

- Chamadas HTTP: [RTK Query | custom hook + axios | React Query | fetch direto | detectado]
- Loading/error state: [Redux store | React Query state | local useState | detectado]
- Formulários: [React Hook Form | Formik | controlled components | detectado]
- Estado global: [Redux Toolkit | Zustand | Context API | detectado]

### Exclusões de Análise

| Ferramenta | Padrão excluído | Fonte                      |
|------------|-----------------|----------------------------|
| SonarQube  | `[padrão]`      | `sonar-project.properties` |
| Jest       | `[padrão]`      | `jest.config.*`            |
| ESLint     | `[padrão]`      | `.eslintignore` / `eslint.config.*` |

### Configurações Relevantes

- tsconfig paths aliases: [lista ou N/A]
- moduleNameMapper (jest): [lista ou N/A]

---

## [SUBREPO] — ex.: BaseVolumes.API (.NET)

### Estrutura de Diretórios

| Tipo de artefato    | Caminho relativo ao workspace    |
|---------------------|----------------------------------|
| Controllers         | `[caminho]/Controllers/`         |
| Business (serviços) | `[caminho]/Business/`            |
| Repositories        | `[projeto Repository]/`          |
| Domain Entities     | `[projeto Domain.Entity]/`       |
| DTOs                | `[projeto Domain.Dto]/`          |
| Testes unitários    | `[projeto *.Tests]/`             |

### Convenções de Nomenclatura

> ⚠️ Inferido por amostragem.

- Controllers: [sufixo `Controller` | detectado]
- Business classes: [sufixo `Business` | detectado]
- Repositories: [sufixo `Repository` | detectado]
- Test method naming: [`MethodName_State_Expected` | detectado]
- Padrões específicos detectados: [ex.: `XxxRequest`/`XxxResponse` para DTOs de endpoint | N/A]

### Composição Interna

> ⚠️ Inferido por amostragem de 2-3 arquivos de cada tipo.

**Business class:**
- Injeção de dependências: [construtor | property injection | detectado]
- Validação: [inline por método | FluentValidation chamado no início | detectado]
- Organização de métodos: [detectado — ex.: públicos antes dos privados]

**Controller action:**
- Tratamento de erro: [try/catch por método | global exception filter | Result pattern | detectado]
- Validação de entrada: [pipeline automático FluentValidation | manual no método | detectado]

### Padrões Relacionais

> ⚠️ Inferido por amostragem.

- Mapeamento DTO↔Entity: [AutoMapper com Profile | extensões manuais `MapTo...` | detectado]
- Exposição de API interna entre projetos: [por interface pública | por namespace | detectado]

### Soluções para Problemas Recorrentes

> ⚠️ Inferido por presença de arquivos de setup e amostragem de uso.

- Validação: [FluentValidation | DataAnnotations | custom | detectado]
- Tratamento de exceções: [global exception filter | middleware | try/catch por método | detectado]
- Mapeamento: [AutoMapper | extensões manuais | detectado]
- Autenticação/autorização: [JWT via atributo `[Authorize]` | policy-based | detectado]

### Exclusões de Análise

| Ferramenta | Padrão excluído | Fonte                            |
|------------|-----------------|----------------------------------|
| SonarQube  | `[padrão]`      | `sonar-project.properties`       |
| Cobertura  | `[padrão]`      | `.runsettings` / `coverlet.json` |
