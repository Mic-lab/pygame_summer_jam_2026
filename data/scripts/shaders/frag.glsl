#version 330 core

uniform sampler2D canvasTex;
uniform sampler2D perlinNoise;
uniform float time;
uniform float transitionTimer;
uniform int transitionState;
uniform float shakeTimer = -1.0;
uniform float caTimer = -1.0;
in vec2 uvs;
out vec4 f_color;

const float PI = 3.14159265359;
const vec2 gridSize = vec2(64, 64);
const vec2 screenSize = vec2(640, 360);
const float caCoef = 0.005;
const float shakeCoef = 0.01;

vec2 rotateVec(vec2 vec, float theta) {
    return vec.x * vec2(cos(theta), sin(theta))
    + vec.y * vec2(sin(theta), -cos(theta));
}

float linearEase(float x) {
    return -2*abs(x - 0.5) + 1;
}

void main() {
    f_color = vec4(texture(canvasTex, uvs).rgb, 1.0);
    if (distance(f_color.rgb, vec3(0.251, 0.486, 0.663)) < 0.05) {
        float scroll = time * 0.00001;
        vec2 noise_uvs = floor(uvs * screenSize) / screenSize;
        vec2 flow_1 = noise_uvs + vec2(sin(scroll), cos(scroll));
        vec2 flow_2 = noise_uvs - vec2(cos(scroll), -sin(scroll));

        float noise = (texture(perlinNoise, flow_1 * 2.0).r + texture(perlinNoise, flow_2 * 2.0).r) * 0.5;
        if (noise >= 0.42 && noise <= 0.58) {
            f_color.rgb = vec3(0.569, 0.639, 0.812);
        }
    }
    float centerDist = distance(uvs, vec2(0.5, 0.5));

    // Blurry shake
    if (shakeTimer >= 0) {
        float shakeIntensity = (1 - shakeTimer)*centerDist * shakeCoef;
        vec2 shakeSampleVec = vec2(0.0, shakeIntensity);
        vec4 caSample1 = texture(canvasTex, uvs + shakeSampleVec);
        vec4 caSample2 = texture(canvasTex, uvs - rotateVec(shakeSampleVec, 2.0*PI/3.0));
        vec4 caSample3 = texture(canvasTex, uvs - rotateVec(shakeSampleVec, 4.0*PI/3.0));
        vec4 sampleMix = mix( mix(caSample1, caSample2, 0.5), caSample3, 0.5 );
        f_color = mix(f_color, sampleMix, 0.5);
    }

    // Chromatic abberation
    if (caTimer >= 0.0) {
        float caIntensity = caTimer*centerDist * caCoef;
        vec2 sampleVec = vec2(0.0, caIntensity);
        float caSample1 = texture(canvasTex, uvs + sampleVec).r;
        float caSample2 = texture(canvasTex, uvs - rotateVec(sampleVec, 2.0*PI/3.0)).g;
        float caSample3 = texture(canvasTex, uvs - rotateVec(sampleVec, 4.0*PI/3.0)).b;
        f_color.r = caSample1;
        f_color.g = caSample2;
        f_color.b = caSample3;
    }

    /*
    0  No transition
    1  Starting transition
    -1 Ending transition
    */
    if (transitionState != 0) { 
        float tTimer = transitionTimer;
        if (transitionState == 1) {
            tTimer = 1.0 - transitionTimer;
        }
        f_color.r *= clamp(tTimer, 0, 1);
        f_color.g *= clamp(1.5*tTimer, 0, 1);
        f_color.b *= clamp(2*tTimer, 0, 1);
        // f_color *= tTimer;
        // f_color.rb *= tTimer;

    }
}

