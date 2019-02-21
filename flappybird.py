from pynf.flappybird import game

Game = game.Engine('flappybird.json')

Game.InitWindow()

while not(Game.Over()):
    Game.Update()

Game.CloseWindow()