const int laserPin = 7;

const int redPin = 9;
const int greenPin = 10;
const int bluePin = 11;
const int buzzerPin = 8;
const int ldrPin = A0;

// Threshold 
int threshold = 25;

void setColor(int r, int g, int b){
  analogWrite(redPin, 255 - r);
  analogWrite(greenPin, 255 - g);
  analogWrite(bluePin, 255 - b);
}


bool detectIntrusion(){

  int count = 0;

  for(int i=0;i<20;i++){

    int value = analogRead(ldrPin);

    if(value > threshold){
      count++;
    }

    delay(30);
  }

  return (count > 15);
}

void buzzerAlarm(){

  for(int i=0;i<2;i++){

    tone(buzzerPin, 2000);
    delay(120);

    noTone(buzzerPin);
    delay(120);
  }
}


void alarmAnimation(){

  unsigned long startTime = millis();

  while(millis() - startTime < 2000){ // 10 secondes

    // Rouge
    setColor(255,0,0);
    delay(200);

    // Orange
    setColor(255,80,0);
    delay(200);
  }
  buzzerAlarm();

  // Retour état normal → Vert
  setColor(0,255,0);
}


void setup(){

  pinMode(laserPin, OUTPUT);

  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);

  pinMode(buzzerPin, OUTPUT);

  Serial.begin(9600);

  setColor(0,255,0);
}

void loop(){

  int ldrValue = analogRead(ldrPin);

  // Afficher valeur LDR en continu
  Serial.println(ldrValue);
  
  if(detectIntrusion()){
    Serial.println("INTRUSION");
    alarmAnimation();
  }
  else{
    setColor(0,255,0);
  }
  delay(200);
}