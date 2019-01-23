from flappybird.game import engine

Game = engine('settings.json')

Game.InitWindow()

#while not(Game.Over()):
Game.Update()

Game.CloseWindow()