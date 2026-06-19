# Checklist manual — tornar o repositório público (discreto)

> Tudo que o Claude **não** consegue fazer por você (mudanças de configuração no
> site do GitHub) ou que ele **não deve** fazer sozinho (apagar branches remotos).
> Faça **nesta ordem**. O objetivo é reduzir descoberta casual — **não** é
> segurança real: qualquer pessoa com o link verá tudo.
>
> ⚠️ **Antes de virar público:** confirme que o PR `chore/prepare-public-release`
> já foi mergeado no `main` (ele tira os dados de resultado do repositório e
> neutraliza o README).

## 0. Pré-checagem (1 min)

- [ ] O PR `chore/prepare-public-release` está **mergeado** no `main`.
- [ ] Apagar os branches remotos antigos (nomes revelam estratégia na lista de
      branches do repo público). O Claude **não** apaga branch remoto — rode você
      mesmo no terminal local. São 29 branches além de `main`:

      ```bash
      git push origin --delete chore/gitignore-resume-json
      git push origin --delete claude/doc-pokemontcg-key-location
      git push origin --delete claude/eloquent-mendel-akwqbe
      git push origin --delete claude/epic-brahmagupta-212NZ
      git push origin --delete claude/intelligent-albattani-owksp
      git push origin --delete claude/jolly-planck-eayv20
      git push origin --delete claude/kind-pascal-Pv0do
      git push origin --delete claude/laughing-clarke-CUWWF
      git push origin --delete claude/loving-dirac-icxqoc
      git push origin --delete claude/myp-cards-scanner-AcokQ
      git push origin --delete claude/myp-cards-scanner-results-ijSVp
      git push origin --delete claude/myp-scanner-frequent-deals-6p1Li
      git push origin --delete claude/myp-scanner-principal-sets-Ww4YI
      git push origin --delete claude/real-tcg-price-pokemontcg
      git push origin --delete claude/review-myp-scanner-status-LUiwu
      git push origin --delete claude/scanner-a3-realprice-gate
      git push origin --delete claude/scanner-resume
      git push origin --delete claude/session-handoff-LUiwu
      git push origin --delete claude/sleepy-gates-MJIBF
      git push origin --delete claude/v5810-code-health
      git push origin --delete claude/wire-pokemontcg-key
      git push origin --delete docs/delivery-format-mandatory
      git push origin --delete docs/delivery-rule-chat-only
      git push origin --delete docs/restore-me-finding-and-local-key
      git push origin --delete feat/v5.13-coverage-fpr
      git push origin --delete fix/reviewer-quickfixes
      git push origin --delete min-price-floor-50
      git push origin --delete results/black-bolt-2026-06-17
      git push origin --delete threshold-30-gross-margin
      ```

      (Antes de apagar, confirme que nenhum tem trabalho não-mergeado que você
      ainda quer — quase todos já estão no `main`.)

## 1. Renomear o repositório (nome menos óbvio)

- [ ] `Settings → General → Repository name` → trocar
      `myp-arbitrage-scanner` por algo neutro, ex.: `price-compare-tool`
      ou `pc-utils`.
- [ ] Atualizar o `git remote` local depois:
      ```bash
      git remote set-url origin https://github.com/matheuscllm-lgtm/<novo-nome>.git
      ```
- [ ] (O GitHub cria redirect do nome antigo; se quiser cortar isso, evite usar
      o nome antigo em links públicos.)

## 2. Remover description e topics

- [ ] Na página inicial do repo → engrenagem ⚙️ ao lado de "About".
- [ ] Apagar a **Description**.
- [ ] Apagar todos os **Topics** (tags).

## 3. Desligar features que criam superfície pública

- [ ] `Settings → General → Features`:
  - [ ] **Issues** → desligar.
  - [ ] **Wikis** → desligar.
  - [ ] **Discussions** → desligar.
  - [ ] **Projects** → desligar.
- [ ] `Settings → Pages` → Source = **None** (confirmar que Pages está desligado).

## 4. Conferir secrets de CI (antes de publicar)

- [ ] `Settings → Secrets and variables → Actions` → confirmar que existem
      `POKEMONTCG_API_KEY` e `FIRECRAWL_API_KEY` (necessários só para os
      workflows de scan; o workflow de **tests** não usa secret).
- [ ] Lembre: em repo **público**, os **logs e artifacts** de cada run dos
      workflows de scan ficam baixáveis por qualquer um que achar o repo —
      e os artifacts agora contêm o markdown de resultados (deal data). Para
      resultados realmente privados, rode o scan **local** (venv + key no
      ambiente), não no Actions.

## 5. Tornar público

- [ ] `Settings → General → Danger Zone → Change repository visibility`
      → **Make public** → confirmar digitando o nome.

## 6. Validar que o Actions roda de graça

- [ ] Aba **Actions** → workflow **tests** deve rodar sozinho no próximo push/PR
      (ou rode via "Run workflow") e ficar **verde**, em runner `ubuntu-latest`.
- [ ] `Settings → Billing` → confirmar que minutos de Actions de repo público
      **não** consomem cota paga (são gratuitos).
- [ ] Rodar um `quick-scan` manual (`gh workflow run quick-scan.yml`) e conferir
      que ele **não** commita nada no `main` (resultado sai só como artifact).

## 7. Pós-publicação (higiene)

- [ ] Rotacionar `POKEMONTCG_API_KEY` / `FIRECRAWL_API_KEY` se houver qualquer
      dúvida sobre exposição passada (gerar novo valor no provedor; atualizar o
      secret no GitHub e a env var local).
- [ ] Conferir a aba **Actions → artifacts** e apagar artifacts antigos de scan
      que tenham ficado de runs anteriores (eles contêm deal data).
