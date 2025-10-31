# TERM64
A morden replica for TRS-80 Model 100.

创造一个以世界第一款商业成功的笔记本计算机TRS-80 Model 100和它的姐妹机型Olivetti M-10为灵感原型的，基于树莓派5的终端设备。


<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/1e9111cc-c9e0-4ab2-a120-a2e717a15338" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/9bcea0fe-5a74-4bb6-b598-2f505a1407f6" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/a731b42d-b47c-413a-9029-3ca28d66d781" />


## 文件说明

- 在Model_25文件夹中3D_Model目录中包含了设计的源文件（可以用SketchUp打开）以及可直接打印的STL和3MF文件。 （铰链打印建议使用PC材料）

- 在TELCOM_Application文件夹中，则是用来和TRS-80 Model 100串口通讯的软件以及协助它连上DeepSeek的程序的源代码。

## 相关硬件

### 树莓派5

Model 25需要使用树莓派5作为计算核心。
<img width="400" height="301" alt="image" src="https://github.com/user-attachments/assets/f3b6020b-3763-44ad-bdd6-b27d884a108c" />

### 电源

电源分为充电电路和电池两部分。

充电电路使用了Waveshare的树莓派不间断电源供电板（3S串联输出），并拆掉了上面的18650电池盒。
<img width="960" height="576" alt="image" src="https://github.com/user-attachments/assets/9046abb9-0f81-4bcd-becc-adf7531ba2e5" />

由于树莓派5对电流要求较高，电池使用了动力锂电池，尺寸规格为 85*67*6.2mm，数量为3块。
<img width="592" height="437" alt="image" src="https://github.com/user-attachments/assets/7849ae1d-7cda-4ce3-9bfa-7814542fd0c6" />

电池焊接时注意安全，尽量使用点焊，不要长时间加热极板。

### 键盘

键盘使用40%机械键盘通过USB连接到树莓派的USB2.0接口。
<img width="750" height="348" alt="image" src="https://github.com/user-attachments/assets/d2fcbf75-2257-402d-ab1b-8328ed51ff7c" />

USB连接使用超薄隐形FPC USB连接线。Type A公头转Type C公头。
<img width="750" height="563" alt="image" src="https://github.com/user-attachments/assets/faf069ca-b635-492c-bc0c-5d8a95ef3257" />

键轴和键帽可以根据自己的喜好随意选择。

### 显示屏

显示屏使用6.8寸 1280*480分辨率的带触摸和HDMI口的液晶显示屏。显示屏通过超薄FPC HDMI线和超薄FPC USB线与树莓派连接。

<img width="750" height="788" alt="image" src="https://github.com/user-attachments/assets/ca6b3a53-c0c3-44db-85aa-ad2ab50a9206" />

HDMI线，需要选择15cm长，HDMI直对microhdmi直头带屏蔽软排线。
<img width="750" height="960" alt="image" src="https://github.com/user-attachments/assets/846ec6ca-56d7-42fc-b436-ea5c47b7aab6" />
<img width="371" height="415" alt="image" src="https://github.com/user-attachments/assets/1bfec09f-7730-44b5-ba41-c71be4e42dfc" />
<img width="358" height="363" alt="image" src="https://github.com/user-attachments/assets/0126b2ae-9030-4cf0-a33c-6e32d832596c" />

USB线和上面键盘连接线一样，使用超薄隐形USB线，USB Type A公头转Micro USB 公头。Type A 那一头插在树莓派的USB2.0口。FPC排线要略长一些。
<img width="750" height="563" alt="image" src="https://github.com/user-attachments/assets/faf069ca-b635-492c-bc0c-5d8a95ef3257" />

以上软排线通过液晶显示屏外壳的线槽孔连接到主机壳内部，穿线走线、折弯时注意不要折断。

### 声音

声音系统是通过HDMI接口传递到显示屏，并在显示屏的3.5mm音频接口输出的。需要制作一个3.5mm的音频插头，将声音输入到功放电路，然后再输出到扬声器。

功放电路使用了PAM8403功放模块。可以安装在液晶显示屏外壳内。
<img width="658" height="517" alt="image" src="https://github.com/user-attachments/assets/40af22a9-8149-41a4-ad84-2549ca4d03ca" />

声音纯净的秘诀是攻防系统独立隔离供电，因此可以在主机使用的Waveshare的电源供电板上，从BAT接口引出11V的电源（3S直接输出），并使用一个DC-DC降压模块，输出5V3A的电流

HLK-B1205S-3WR3
<img width="830" height="402" alt="image" src="https://github.com/user-attachments/assets/621c617b-c4bf-474a-a5df-dcb458a633f5" />

电源输出端可以通过一个1mm间距的6P的FPC软排线通过线控输出到显示屏外壳中的PAM8403功放模块。为了确保大电流传送，可以将6P软排线的其中三根并接5V，另外三根并接GND。
<img width="508" height="498" alt="image" src="https://github.com/user-attachments/assets/4a6cc9c4-041d-4796-b53a-ae3fe0d58855" />
<img width="805" height="609" alt="image" src="https://github.com/user-attachments/assets/2a8f14a2-cad1-4863-a4e1-ee5cd7fc22eb" />

扬声器的部分，使用了3020腔体扬声器，4欧3瓦。可以安装在显示屏外壳内的座子上。
<img width="499" height="492" alt="image" src="https://github.com/user-attachments/assets/f2496b46-c4e2-4e36-8e24-30f0550b54b2" />


## 免责声明

所有设计和代码均为测试和实验性质，以技术交流为目的，本人对所有设计、代码以及相关衍生物的功能性、有效性、可靠性均不做任何保证。也不对任何外延的结果、效果及产生的影响承担任何责任。

## 许可证

基于GNU GPLv3协议发布，如二次分发，请遵守协议内容。详情请参考LICENSE文件。


