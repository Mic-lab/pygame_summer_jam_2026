#version 330 core

uniform sampler2D canvasTex;
uniform sampler2D perlinNoise;
uniform float time;
// uniform int scale;
uniform float transitionTimer = -1.0;
uniform float levelTransitionTimer = -1.0;
uniform int transitionState = 0;
uniform float shakeTimer = -1.0;
uniform float caTimer = -1.0;
uniform float flashTimer = -1.0;
uniform float restartTimer = -1.0;
uniform float hitTimer = -1.0;
uniform vec2[32] beamCoords;
in vec2 uvs;
out vec4 f_color;

const float PI = 3.14159265359;
const vec2 gridSize = vec2(64, 64);
const vec2 screenSize = vec2(640, 360);
const float caCoef = 0.005;
const float shakeCoef = 0.01;
const vec3 purpleColor1 = vec3(53, 1, 75)/255;
const vec3 purpleColor2 = vec3(124, 1, 114)/255;

vec2 rotateVec(vec2 vec, float theta) {
    return vec.x * vec2(cos(theta), sin(theta))
    + vec.y * vec2(sin(theta), -cos(theta));
}

float linearEase(float x) {
    return -2*abs(x - 0.5) + 1;
}

vec2 normalizeScreenVec(vec2 v) {
    return v/screenSize.x;
}

void main() {
    f_color = vec4(texture(canvasTex, uvs).rgb, 1.0);

    vec2 uvsS = vec2(uvs.x, uvs.y * screenSize.y/screenSize.x);
    vec2 uvsSPx = vec2(floor(uvsS*screenSize.x)/screenSize.x);
    float centerDist = distance(uvs, vec2(0.5, 0.5));

    // Chromatic abberation
    // float ca = caTimer*0.0001+0.8;
    float ca = caTimer;
    if (ca >= 0.0) {
        float caIntensity = ca*centerDist * caCoef;
        vec2 sampleVec = vec2(0.0, caIntensity);
        float caSample1 = texture(canvasTex, uvs + sampleVec).r;
        float caSample2 = texture(canvasTex, uvs - rotateVec(sampleVec, 2.0*PI/3.0)).g;
        float caSample3 = texture(canvasTex, uvs - rotateVec(sampleVec, 4.0*PI/3.0)).b;
        f_color.r = caSample1;
        f_color.g = caSample2;
        f_color.b = caSample3;
    }

    // Lava
    int apply_lava_bloom = 1;
    if (distance(f_color.rgb, vec3(1.000, 0.000, 0.000)) < 0.05) {
        float scroll = time * 0.00002;
        vec2 noise_uvs = floor(uvs * screenSize) / screenSize;
        vec2 flow_1 = noise_uvs + vec2(sin(scroll), cos(scroll));
        vec2 flow_2 = noise_uvs - vec2(cos(scroll), -sin(scroll));

        float noise = (texture(perlinNoise, flow_1 * 2.0).r + texture(perlinNoise, flow_2 * 2.0).r) * 0.5;
        if (noise >= 0.45 && noise <= 0.55) {
            f_color.rgb = vec3(1.000, 0.992, 0.796);
        } else if (noise <= 0.4) {
            f_color.rgb = vec3(0.745, 0.114, 0.278);
        } else {
            f_color.rgb = vec3(1.00, 0.639, 0.247);
        };

        apply_lava_bloom = 0;
    }

    int bloom = 0;
    float dist = 0;
    float nx = texture(perlinNoise, uvs+vec2(time*0.00001)).r;
    float ny = texture(perlinNoise, uvs*3+vec2(time*0.000015)).r;
    for (float i = 0.; i < 5.; i += 0.25) {
        vec2 offset = vec2(
                mix(-0.005, 0.005, nx),
                mix(0, 0.04, ny));
        if (distance(texture(canvasTex, uvs + vec2(0, i/100)+offset).rgb, vec3(1.000, 0.000, 0.000)) < 0.05) {
            dist = i;
            bloom = 1;
            break;
        };
    };

    f_color.rgb += vec3(1.00, 0.639, 0.247) * 0.2 * (1. - (dist / 5.)) * bloom * apply_lava_bloom;

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


    float beamNoise1 = texture(perlinNoise, vec2(uvsSPx)*0.0005*time).r;
    float beamNoise2 = texture(perlinNoise, vec2(uvsSPx)*0.001*time).r;
        
    // Beam
    // beamCoords: ((Ax1, Ay1), (Bx1, By1), (Ax2, Ay2), ...)
    for (int i = 0; i < beamCoords.length(); i+=2) {
        vec2 beamCoordA = beamCoords[i];
        if (beamCoordA == vec2(-1, -1)) {break; }

        vec2 beamCoordB = beamCoords[i+1];
        vec2 a = normalizeScreenVec(beamCoordA);
        vec2 b = normalizeScreenVec(beamCoordB);


        // Get the projection of uvs onto a-b if `a` is considered as the origin
        vec2 line = b-a;  // (b-a)-(a-a)
        vec2 uvsProj = line * (dot(uvsSPx-a, line) / dot(line, line));
        // If projection not aligned with the line
        if (dot(uvsProj, line) < 0) {
            uvsProj *= 0;
        }
        else {
            uvsProj /= length(uvsProj) / min(length(uvsProj), length(line));
        }
        vec2 lineDist = (uvsSPx-a)-uvsProj;

        float d = length(lineDist);
        if (d < 0.013+abs(beamNoise1-0.5)*0.005) {
            f_color *=3;
            f_color.rgb = mix(f_color.rgb, vec3(0.8, 0.9, 1), 0.4);
            }
        }


    // Win flash
    if (flashTimer > 0) {
        float intensity = mix(1, 0.8, pow(flashTimer, 5));
        f_color.r = pow(f_color.r, intensity);
        f_color.g = pow(f_color.g, intensity);
        f_color.b = pow(f_color.b, intensity);
    }

    // Restart timer
    if (restartTimer > 0) {
        vec3 gray = vec3((f_color.r + f_color.g + f_color.b)/3);
        float intensity = mix(0, 1, restartTimer);
        gray.b*=intensity*3;
        f_color.rgb = mix(f_color.rgb, gray, (min(1.4*intensity, 1)));
        f_color *= 1-intensity;
    }

    // Player hit timer
    if (hitTimer > 0) {
        vec3 gray = vec3((f_color.r + f_color.g + f_color.b)/3)*0.5;
        // vec3 gray = vec3(f_color.r, 0, 0);
        float intensity = pow(hitTimer, 2);
        f_color.rgb = mix(f_color.rgb, gray, intensity);
    }

    // Level Transition Timer
    if (levelTransitionTimer > 0) {
        vec3 black = vec3(5, 0, 39)/255;
        float intensity = linearEase(levelTransitionTimer);
        f_color.rgb = mix(f_color.rgb, black, intensity);
    }

    // Vignette + color filters

    // f_color.b = pow(f_color.b, mix(0.2, 1, centerDist));
    // f_color.g = pow(f_color.g, mix(0.6, 1, centerDist));

    // float r = f_color.r;
    // float g = f_color.g;
    // float b = f_color.b;
    // f_color.r = g;
    // f_color.g = r;

    // f_color.r *= 1.3-1.3*centerDist;
    // f_color.b *= 1-0*centerDist;

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

