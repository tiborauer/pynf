# PyNF
Python package for neurofeedback training

#### Author: [Tibor Auer](https://twitter.com/TiborAuer)

## Content
- dicomexport 
  - real-time export of DICOM data via TCP
  - in-memory conversion to 3D volume with 'minimum' header for subsequent registration
- feedback
  - receive activity level over UDP
  - parameterizable double-log function to convert activity level to feedback signal
  - shaping
- flappybird
  - the famous and addictive game based on PsychoPy3
  - parameterizable
  - adaptive based on signal over UDP

## Install
`pip install git+https://github.com/tiborauer/pynf.git`

## Demo
<blockquote class="twitter-tweet" data-lang="en"><p lang="en" dir="ltr">Our first real-time neurofeedback demonstration <a href="https://t.co/2OWxjKcyhz">https://t.co/2OWxjKcyhz</a></p>&mdash; Tibor Auer (@TiborAuer) <a href="https://twitter.com/TiborAuer/status/1105197646854135814?ref_src=twsrc%5Etfw">March 11, 2019</a></blockquote>
