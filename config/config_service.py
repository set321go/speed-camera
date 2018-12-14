import click
import os
import shutil
from config.app_constants import CONFIG_DEFAULTS_FILENAME


def default_dump():
    click.echo("Exporting configuration defaults to the current dir")
    script_dir = os.path.dirname(os.path.realpath(__file__))
    shutil.copyfile(os.path.join(script_dir, CONFIG_DEFAULTS_FILENAME), os.path.join(os.getcwd(), CONFIG_DEFAULTS_FILENAME))


def setup():
    click.echo("The speed cam tool has a full set of defaults so should work without setup")
    click.echo("You may get more accurate and better performance by tweaking your own setup")
    click.echo("For a full list of configuration parameters run <speed-cam config --export-default>")
    click.echo("After setup is complete a config.ini file will be generated with custom values.")
