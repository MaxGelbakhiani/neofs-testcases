### Сборка образа с тестами

Чтобы тесты из этого репозитория были доступны к запуску из Drone CI,
они должны быть упакованы в docker-имадж. Это делается в рамках CI,
сконфигурированного в этом репозитории. Вся сборка "тестового образа"
описывается в файлах `Dockerfile` и `.drone.yml` и осуществляется на
каждый пуш в master.

В докерфайле указана версия `neofs-cli`, который используется в запусках
тестов. Каждый раз при сборке имаджа `neofs-cli` скачивается заново.

Тестовый образ имеет единственную версию -- `latest`. Ради экономии
хранилища на машине-сборщике перед сборкой все ранее собранные образы
удаляются.

#### Локальная сборка
Чтобы локально собрать образ, нужно, стоя в корне репо, выполнить
команду:
```
drone exec --trusted --secret-file=secrets.txt --volume /var/run/docker.sock
```
В результате будет прогнан полный пайплайн, за исключением пуша образа в
docker registry. Чтобы запушить образ, нужно указать пароль к реджистри в
файле `secrets.txt`.
