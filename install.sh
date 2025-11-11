pyinstaller --onefile src/charonte/cli.py \
            --name B-coin \
            --copy-metadata charonte \
            --paths src \
            --collect-all charonte \
            --collect-all pyinfra.operations \
--collect-all passlib \
--collect-all omegaconf \
--collect-all pyinfra.connectors \
--collect-all pyinfra.facts
