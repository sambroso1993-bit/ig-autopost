# IG Reels autopost через GitHub Actions

Автопубликация рилсов в Instagram с **чистого IP GitHub** (обходит блок Meta по РФ-IP).
Токен хранится в **GitHub Secrets** (зашифрован, не в коде). Видео лежат в `reels/`, расписание — в `due.json`.

## Как работает
GitHub по расписанию (cron) запускает `publish.py`: для каждого ролика, у которого наступил слот и он не `done`,
заливает mp4 на litterbox → создаёт REELS-контейнер в Graph API → публикует → ставит `done` и коммитит обратно.
Ограничение: **не более 3 публикаций за один запуск** (чтобы не залить бэклог залпом; меняется переменной `MAX_PER_RUN`).

## Настройка (4 шага, ~5 минут)

**1. Создай репозиторий на github.com**
   - New repository → имя любое (напр. `na-chem-ezdit-ig`).
   - Рекомендую **Public** — тогда минуты GitHub Actions безлимитны (секреты всё равно зашифрованы и не видны). Если хочешь Private — тоже ок, cron стоит редкий (5 раз/день), в бесплатные 2000 мин/мес укладывается.

**2. Запушь эту папку** (`ig-github-poster/`) в репозиторий:
```
cd ig-github-poster
git init
git add .
git commit -m "ig autopost"
git branch -M main
git remote add origin https://github.com/<ТВОЙ_ЛОГИН>/<РЕПО>.git
git push -u origin main
```
(при пуше GitHub попросит логин + Personal Access Token вместо пароля — создаётся в Settings → Developer settings → Tokens)

**3. Добавь 2 секрета** в репозитории:
   Settings → Secrets and variables → **Actions** → New repository secret:
   - `IG_ACCESS_TOKEN` — значение поля `access_token` из твоего `reels_config.json`
   - `IG_USER_ID` — значение поля `ig_user_id` (17841426383502722)
   
   ⚠️ Токен вставляй прямо в поле секрета на GitHub. Никому не пересылай, в код не клади.

**4. Запусти проверку:** вкладка **Actions** → включи workflows (кнопка «I understand… enable») → выбери «IG Reels autopost» → **Run workflow**.
   В логе job'а увидишь `ПУБЛИКУЮ … OK media_id …`. Дальше он работает сам по расписанию.

## Расписание
`.github/workflows/publish.yml`, cron в UTC: `5 7,10,13,16,19 * * *` = МСК 10:05 / 13:05 / 16:05 / 19:05 / 22:05.
Меняй cron под свои слоты. Бэклог (просроченные) публикуется по 3 шт. за запуск, пока не разгребётся.

## Добавить новые ролики позже
На Mac: положи ролики в очередь как обычно, затем
`python3 reels_upload/build_github_due.py` (пересоберёт `reels/` + `due.json` из невыложенного) →
`git add . && git commit -m "new reels" && git push`. GitHub подхватит.

## Если снова «API access blocked» даже здесь
Значит Meta ограничила само приложение (не IP). Тогда: проверь, что токен валиден (не отозван),
и что приложение/IG-аккаунт в порядке в Meta for Developers. IP GitHub-раннеров чистый — гео-блок РФ он снимает.
