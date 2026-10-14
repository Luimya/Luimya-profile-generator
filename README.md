# Private Profile Generator

This private repository contains the generator code and historical versions of the Luimya GitHub profile.

Public display: https://github.com/Luimya

Public repository: https://github.com/Luimya/Luimya

The workflow generates horizontal language charts and contribution-snake animations, then publishes only four SVG assets to the public repository. Generation code and workflow logs remain private.

The scheduled refresh runs at 03:23 UTC (12:23 Japan time). For a manual refresh, select **Update public profile visuals** in Actions and use **Run workflow**.

`PROFILE_DEPLOY_KEY` is an Actions secret containing the encrypted deploy key for the public repository. `PROFILE_KEY_PASSPHRASE` is its runtime unlocking secret. The key is scoped to that repository. Never commit either secret or include them in backup packages. Local unlocking data uses Windows DPAPI rather than a plaintext passphrase file.
