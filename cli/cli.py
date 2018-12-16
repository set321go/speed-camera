import click
import speedcam.speed_cam
import config.config_service
import speedcam.camera.calibration
import inquirer


@click.group()
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo('I was invoked without subcommand')


@cli.command()
def run():
    speedcam.speed_cam.start()


@cli.command()
def setup():
    questions = [
        inquirer.List('options',
                      message="Choose from the following setup options?",
                      choices=['Configure Camera', 'Export Default Config'],
                      ),
    ]

    answers = inquirer.prompt(questions)

    if answers['options'] == 'Export Default Config':
        config.config_service.default_dump()
    elif answers['options'] == 'Configure Camera':
        speedcam.camera.calibration.calibrate()


