import click
import speedcam.speed_cam
import config.config_service


@click.group()
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo('I was invoked without subcommand')


@cli.command()
def run():
    speedcam.speed_cam.start()


@cli.command()
@click.option('--export-defaults', is_flag=True)
def setup(export_defaults):
    if export_defaults:
        config.config_service.default_dump()
    else:
        config.config_service.setup()
