from gtts import gTTS
from pydub import AudioSegment

text = "I DON'T KNOW WHO YOU ARE. I DON'T KNOW WHAT YOU WANT. IF YOU'RE LOOKING FOR RANSOM, I CAN TELL YOU I DON'T HAVE MONEY. BUT WHAT I DO HAVE, I HAVE A VERY PARTICULAR SET OF SKILLS. SKILLS I HAVE ACQUIRED ARE FOR A VERY LONG CAREER. SKILLS THAT MAKE ME A NIGHTMARE FOR PEOPLE LIKE YOU. IF YOU LET MY DAUGHTER GO NOW, THAT'LL BE THE END OF IT. I WILL NOT LOOK FOR YOU, I WILL NOT PURSUE YOU. BUT IF YOU DON'T, I WILL LOOK FOR YOU. I WILL FIND YOU, AND I WILL KILL YOU. GOOD LUCK. GOOD LUCK."
tts = gTTS(text=text, lang='en')
tts.save("test_speech.mp3")

# mp3 → wav 변환
sound = AudioSegment.from_mp3("test_speech.mp3")
sound.export("test_speech.wav", format="wav")

print("✅ wav 파일로 변환 완료!")