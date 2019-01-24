from pynf.flappybird import game

Game = game.Engine('settings.json')

Game.InitWindow()

while not(Game.Over()):
    Game.Update()

Game.CloseWindow()