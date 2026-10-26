# Continuous integration

Create the application's workflow after choosing its actual runtime and toolchain. Pin setup actions to reviewed commit SHAs, use an explicit runtime version, minimise token permissions, run formatting/lint/build/tests, and keep production credentials out of pull-request jobs.

A workflow must not report success when checks were skipped. Include source/dependency analysis and secret scanning appropriate to the chosen stack. Do not introduce a fake build command merely to make the scaffold look complete.
